#!/usr/bin/env python3
"""Resume a completed native build using the current verified uploader."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def gh(*args):
    return subprocess.check_output(['gh', *map(str, args)], text=True)


def verify_sums(directory):
    seen = set()
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split(None, 1)
        if Path(name).name != name or name in seen:
            raise ValueError('Invalid or duplicate checksum path')
        seen.add(name)
        with (directory / name).open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != expected:
            raise ValueError('Checksum mismatch: ' + name)
    actual_files = {p.name for p in directory.iterdir() if p.is_file()} - {'SHA256SUMS'}
    if not seen or seen != actual_files:
        raise ValueError('Incomplete checksum manifest')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-run', required=True)
    args = parser.parse_args()
    if not args.source_run.isdecimal():
        raise ValueError('Invalid source run')
    repo = os.environ['GITHUB_REPOSITORY']
    info = json.loads(gh('api', f'repos/{repo}/actions/runs/{args.source_run}'))
    if (info['path'] != '.github/workflows/build-openwrt-native.yml'
            or info['head_repository']['full_name'] != repo or info['head_branch'] != 'main'
            or info['status'] != 'completed'):
        raise ValueError('Expected completed same-repository main-branch native build')
    pages = json.loads(gh('api', '--paginate', '--slurp', f'repos/{repo}/actions/runs/{args.source_run}/jobs'))
    if not any(j['name'] == 'build' and j['conclusion'] == 'success'
               for page in pages for j in page['jobs']):
        raise ValueError('Source build did not succeed')
    pages = json.loads(gh('api', '--paginate', '--slurp', f'repos/{repo}/actions/runs/{args.source_run}/artifacts'))
    artifacts = [a for page in pages for a in page['artifacts']
                 if a['name'].startswith('native-') and a['name'].endswith('-release-bundle') and not a['expired']]
    if len(artifacts) != 1:
        raise ValueError('Expected exactly one completed release bundle')
    work = Path(os.environ['NATIVE_WORK'])
    gh('run', 'download', args.source_run, '--repo', repo, '--name', artifacts[0]['name'], '--dir', work)
    lock = json.loads((work / 'lock.json').read_text())
    if lock.get('build_commit') != info['head_sha']:
        raise ValueError('Build source commit mismatch')
    verify_sums(work / 'release')
    feeds = list((work / 'releases').glob('native-kmods-*'))
    if len(feeds) != 1:
        raise ValueError('Expected one module feed')
    verify_sums(feeds[0])
    print('PASS: original image and module feed checksums verified', flush=True)
    env = os.environ.copy()
    env.update(GITHUB_RUN_ID=args.source_run, GITHUB_SHA=info['head_sha'])
    subprocess.run([sys.executable, '-u', str(Path(__file__).with_name('pipeline.py')), 'publish'], env=env, check=True)


if __name__ == '__main__':
    main()
