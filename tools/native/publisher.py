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


class GitHubError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


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
                args += ['-H', 'Content-Type: application/octet-stream', '-H', f'Content-Length: {file.stat().st_size}', '--input', str(file)]
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
                raise GitHubError(status, f'GitHub {method} failed ({status}): {body or result.stderr}')
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

    def transfer(self, tag, release, path):
        if self.last_write is not None:
            time.sleep(max(0, self.interval - (time.monotonic() - self.last_write)))
        self.last_write = time.monotonic()
        try:
            result = subprocess.run(['gh', 'release', 'upload', tag, str(path),
                                     '--repo', self.repo], capture_output=True,
                                    text=True, timeout=300)
        except subprocess.TimeoutExpired as error:
            raise GitHubError(0, f'Upload timed out: {path.name}') from error
        if result.returncode:
            match = re.search(r'HTTP (\d{3})', result.stderr)
            raise GitHubError(int(match[1]) if match else 0, result.stderr)
        asset = self.assets(release['id']).get(path.name)
        if asset is None:
            raise GitHubError(0, f'Upload not visible yet: {path.name}')
        return asset

    def upload(self, tag, release, path):
        for attempt in range(4):
            try:
                asset = self.transfer(tag, release, path)
            except GitHubError as error:
                if error.status != 0 and error.status < 500:
                    raise
                # A failed response can conceal a successful upload. Reconcile
                # before retrying; never replace an existing asset.
                time.sleep(15)
                asset = self.assets(release['id']).get(path.name)
                if asset is not None:
                    if release.get('draft') and asset.get('state') == 'starter':
                        self.api(f"repos/{self.repo}/releases/assets/{asset['id']}", 'DELETE')
                    else:
                        self.verify(tag, path, asset)
                        return
                if attempt == 3:
                    raise
                print(f'Upload absent after server/transport failure; retry {attempt + 1}/3: {path.name}', flush=True)
                time.sleep(15 * (attempt + 1))
                continue
            self.verify(tag, path, asset)
            return

    def publish(self, tag, paths, target, title, notes, prerelease=False):
        paths = {p.name: p for p in paths}
        endpoint = f'repos/{self.repo}/releases'
        release = self.api(f'{endpoint}/tags/{quote(tag, safe="")}')
        if release is None:
            page = 1
            drafts = []
            while True:
                batch = self.api(f'{endpoint}?per_page=100&page={page}')
                drafts.extend(r for r in batch if r['tag_name'] == tag)
                if len(batch) < 100:
                    break
                page += 1
            if len(drafts) > 1:
                raise RuntimeError('Multiple release drafts for tag; inspect before continuing')
            if drafts:
                release = drafts[0]
        if release is None:
            release = self.api(endpoint, 'POST', dict(tag_name=tag, target_commitish=target,
                               name=title, body=notes, draft=True, prerelease=prerelease))
        assets = self.assets(release['id'])
        if set(assets) - set(paths):
            raise RuntimeError('Existing release has unexpected assets; inspect before continuing')
        for name, asset in list(assets.items()):
            if release['draft'] and asset.get('state') == 'starter':
                print(f'Removing unfinished upload: {name}', flush=True)
                self.api(f"repos/{self.repo}/releases/assets/{asset['id']}", 'DELETE')
                del assets[name]
        for name, path in paths.items():
            if name in assets:
                self.verify(tag, path, assets[name])
            elif not release['draft']:
                raise RuntimeError('Published immutable release is incomplete')
        for name, path in sorted(paths.items()):
            if name in assets:
                continue
            print(f'Uploading {tag}: {name}', flush=True)
            self.upload(tag, release, path)
        # Check the complete server-side set before making the release public.
        assets = self.assets(release['id'])
        if set(assets) != set(paths):
            raise RuntimeError('Release asset set is incomplete')
        for name, path in paths.items():
            self.verify(tag, path, assets[name])
        if release['draft']:
            self.api(f"{endpoint}/{release['id']}", 'PATCH', dict(draft=False, make_latest='false'))
        print(f'Published and verified: {tag}', flush=True)
