#!/usr/bin/env python3
"""Publish completed same-repository LibreELEC artifacts, without rebuilding."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from native.publisher import GitHub

def gh(*args):
    return subprocess.check_output(['gh', *map(str, args)], text=True)

def verify(directory):
    directory = Path(directory)
    images = directory / 'libreelec-images'
    manifest = json.loads((images / 'images.json').read_text())
    if set(manifest) != {'sd', 'emmc', 'sd_emmc_installer'}:
        raise ValueError('Expected exactly three image roles')
    sums = {}
    for line in (images / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(None, 1)
        if name in sums:
            raise ValueError('Duplicate checksum entry')
        sums[name] = digest
    assets = []
    for role, item in manifest.items():
        name = item['file']
        if Path(name).name != name or not name.endswith('.img.gz'):
            raise ValueError('Invalid asset name')
        path = images / name
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != item['sha256'] or sums.get(name) != actual:
            raise ValueError('Compressed checksum mismatch: ' + role)
        with gzip.open(path, 'rb') as stream:
            raw = hashlib.file_digest(stream, 'sha256').hexdigest()
        if raw != item['raw_sha256']:
            raise ValueError('Raw checksum mismatch: ' + role)
        assets.append(path)
    if set(sums) != {item['file'] for item in manifest.values()}:
        raise ValueError('Unexpected checksums')
    installer = manifest['sd_emmc_installer']
    if installer.get('os') != 'libreelec' or installer.get('payload_verified') is not True:
        raise ValueError('Installer verification missing')
    for role in ('sd', 'emmc'):
        if installer.get(role + '_source_sha256') != manifest[role]['sha256']:
            raise ValueError('Installer source mismatch')
    return assets + [images / 'images.json', images / 'SHA256SUMS',
                     directory / 'libreelec-request.json', directory / 'libreelec/t95h-port.json']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-run', required=True)
    args = parser.parse_args()
    if not args.source_run.isdecimal():
        raise ValueError('Invalid source run')
    repo = os.environ['GH_REPO']
    info = json.loads(gh('api', f'repos/{repo}/actions/runs/{args.source_run}'))
    if (info['conclusion'] != 'success' or info['path'] != '.github/workflows/build-libreelec.yml'
            or info['head_repository']['full_name'] != repo or info['head_branch'] != 'main'):
        raise ValueError('Expected successful main-branch LibreELEC build from this repository')
    directory = ROOT / 'build' / ('libreelec-publish-' + args.source_run)
    gh('run', 'download', args.source_run, '--repo', repo, '--name',
       't95h-libreelec-base-B-candidates', '--dir', directory)
    assets = verify(directory)
    print('PASS: SD, eMMC and combined installer checksums verified', flush=True)
    client = GitHub(repo)
    tag = f"libreelec-{args.source_run}-{info['run_attempt']}"
    releases = json.loads(gh('api', '--paginate', f'repos/{repo}/releases', '--slurp'))
    existing = next((r for page in releases for r in page if r['tag_name'] == tag), None)
    publication_commit = os.environ.get('GITHUB_SHA') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    provenance_data = {'run': args.source_run, 'commit': info['head_sha'],
        'attempt': info['run_attempt'], 'url': info['html_url'],
        'publication_commit': publication_commit,
        'checksums_verified': True, 'hardware_tested': False}
    # A resumed publication must preserve the original provenance bytes.
    previous = next((a for a in existing.get('assets', [])
                     if a['name'] == 'release-source.json' and a['state'] == 'uploaded'), None) if existing else None
    provenance = directory / 'release-source.json'
    if previous:
        raw = gh('api', '-H', 'Accept: application/octet-stream',
                 f"repos/{repo}/releases/assets/{previous['id']}")
        old = json.loads(raw)
        for key in ('run', 'commit', 'attempt', 'url', 'checksums_verified', 'hardware_tested'):
            if old.get(key) != provenance_data[key]:
                raise ValueError('Existing release provenance mismatch: ' + key)
        provenance.write_text(raw)
    else:
        provenance.write_text(json.dumps(provenance_data, indent=2) + '\n')
    assets.append(provenance)
    client.publish(tag, assets, publication_commit, 'T95H LibreELEC – SD und eMMC',
                   (ROOT / 'docs/libreelec-release-notes.md').read_text(), prerelease=True)
    print(f'https://github.com/{repo}/releases/tag/{tag}')

if __name__ == '__main__':
    main()
