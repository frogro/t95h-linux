"""Paced, resumable release uploads. Never replace an existing asset."""
import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import quote


def digest(path):
    with path.open('rb') as stream:
        return 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()


def retry_delay(headers, attempt, now=None):
    now = time.time() if now is None else now
    if 'retry-after' in headers:
        return max(1, float(headers['retry-after'])) + 1
    if headers.get('x-ratelimit-remaining') == '0' and 'x-ratelimit-reset' in headers:
        return max(1, float(headers['x-ratelimit-reset']) - now) + 1
    return min(3600, 60 * 2 ** attempt)


class GitHub:
    def __init__(self, repo, interval=8):
        self.repo = repo
        self.interval = interval  # <=450 writes/hour, before request overhead
        self.last_write = None

    def api(self, endpoint, method='GET', payload=None, file=None):
        for attempt in range(9):
            if method != 'GET':
                if self.last_write is not None:
                    time.sleep(max(0, self.interval - (time.monotonic() - self.last_write)))
                self.last_write = time.monotonic()
            args = ['gh', 'api', '--include', '--method', method, endpoint]
            data = None
            if file is not None:
                args += ['-H', 'Content-Type: application/octet-stream', '--input', str(file)]
            elif payload is not None:
                args += ['--input', '-']
                data = json.dumps(payload)
            result = subprocess.run(args, input=data, capture_output=True, text=True)
            raw = result.stdout.replace('\r\n', '\n')
            head, _, body = raw.partition('\n\n')
            match = re.match(r'HTTP/\S+ (\d+)', head)
            status = int(match[1]) if match else 0
            headers = dict((k.lower(), v.strip()) for line in head.splitlines()[1:]
                           if ':' in line for k, v in [line.split(':', 1)])
            if result.returncode == 0:
                return json.loads(body) if body.strip() else None
            if status == 404 and method == 'GET':
                return None
            message = (body + result.stderr).lower()
            limited = status == 429 or (status == 403 and ('rate limit' in message or headers.get('x-ratelimit-remaining') == '0'))
            # Only reads retry ambiguous transport/server failures. Uploads are
            # reconciled on the next job attempt, avoiding duplicate writes.
            transient_read = method == 'GET' and (status == 0 or status >= 500)
            if attempt == 8 or not (limited or transient_read):
                raise RuntimeError(f'GitHub {method} failed ({status}): {body or result.stderr}')
            delay = retry_delay(headers, attempt)
            print(f'GitHub limit/transient read error; retry in {delay:.0f}s', flush=True)
            time.sleep(delay)

    def assets(self, release_id):
        assets = []
        page = 1
        while True:
            batch = self.api(f'repos/{self.repo}/releases/{release_id}/assets?per_page=100&page={page}')
            if batch is None:
                raise RuntimeError('Release disappeared while listing assets')
            assets.extend(batch)
            if len(batch) < 100:
                return {asset['name']: asset for asset in assets}
            page += 1

    def verify(self, tag, path, asset):
        if asset.get('state') != 'uploaded' or asset['size'] != path.stat().st_size:
            raise RuntimeError(f'Incomplete or different existing asset: {path.name}')
        expected = digest(path)
        actual = asset.get('digest')
        if not actual:
            # Older assets may not have a server-side digest. Download through
            # gh so authentication/redirect handling stays with the client.
            with tempfile.TemporaryDirectory() as tmp:
                subprocess.run(['gh', 'release', 'download', tag, '--repo', self.repo,
                                '--pattern', path.name, '--dir', tmp], check=True)
                actual = digest(Path(tmp) / path.name)
        if actual != expected:
            raise RuntimeError(f'Immutable asset differs: {path.name}')

    def publish(self, tag, paths, target, title, notes, prerelease=False):
        paths = {p.name: p for p in paths}
        endpoint = f'repos/{self.repo}/releases'
        release = self.api(f'{endpoint}/tags/{quote(tag, safe="")}')
        if release is None:
            release = self.api(endpoint, 'POST', dict(tag_name=tag, target_commitish=target,
                               name=title, body=notes, draft=True, prerelease=prerelease))
        assets = self.assets(release['id'])
        if set(assets) - set(paths):
            raise RuntimeError('Existing release has unexpected assets; inspect before continuing')
        for name, path in paths.items():
            if name in assets:
                self.verify(tag, path, assets[name])
            elif not release['draft']:
                raise RuntimeError('Published immutable release is incomplete')
        for name, path in sorted(paths.items()):
            if name in assets:
                continue
            print(f'Uploading {tag}: {name}', flush=True)
            url = release['upload_url'].split('{')[0] + '?name=' + quote(name, safe='')
            asset = self.api(url, 'POST', file=path)
            self.verify(tag, path, asset)
        # Check the complete server-side set before making the release public.
        assets = self.assets(release['id'])
        if set(assets) != set(paths):
            raise RuntimeError('Release asset set is incomplete')
        for name, path in paths.items():
            self.verify(tag, path, assets[name])
        if release['draft']:
            self.api(f"{endpoint}/{release['id']}", 'PATCH', dict(draft=False, make_latest='false'))
        print(f'Published and verified: {tag}', flush=True)
