#!/usr/bin/env python3
"""Verify and publish completed Anotter images, including upload-only recovery."""
import argparse
import gzip
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from native.publisher import GitHub


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    sums = {}
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(None, 1)
        if Path(name).name != name or name in sums:
            raise ValueError('Invalid or duplicate checksum filename')
        if sha(directory / name) != digest:
            raise ValueError('Checksum mismatch: ' + name)
        sums[name] = digest
    images = [dict(file=manifest['image'], sha256=manifest['sha256'],
                   raw_sha256=manifest['raw_sha256']),
              manifest['emmc'], manifest['sd_emmc_installer']]
    if len({x['file'] for x in images}) != 3:
        raise ValueError('Expected distinct SD, eMMC and combined images')
    for item in images:
        name = item['file']
        if Path(name).name != name or not name.endswith('.img.gz'):
            raise ValueError('Invalid image filename')
        if sums.get(name) != item['sha256']:
            raise ValueError('Manifest/checksum mismatch: ' + name)
        with gzip.open(directory / name, 'rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != item['raw_sha256']:
                raise ValueError('Uncompressed image mismatch: ' + name)
    installer = images[2]
    if installer.get('os') != 'anotter' or installer.get('payload_verified') is not True:
        raise ValueError('Installer verification missing')
    if (installer.get('sd_source_sha256') != images[0]['sha256'] or
            installer.get('emmc_source_sha256') != images[1]['sha256']):
        raise ValueError('Installer does not match SD/eMMC images')
    if json.loads((directory / 'installer.json').read_text()) != installer:
        raise ValueError('Installer metadata differs')
    paths = sorted(directory.iterdir())
    if any(not p.is_file() or p.is_symlink() for p in paths):
        raise ValueError('Expected regular release files only')
    return paths


def source_info(repo, run):
    def api(path):
        return json.loads(subprocess.check_output(['gh', 'api', path], text=True))
    info = api(f'repos/{repo}/actions/runs/{run}')
    if (info['path'] != '.github/workflows/build-anotter.yml' or
            info['head_repository']['full_name'] != repo or info['head_branch'] != 'main'):
        raise ValueError('Expected this repository main-branch Anotter build')
    jobs = api(f'repos/{repo}/actions/runs/{run}/attempts/{info["run_attempt"]}/jobs')['jobs']
    required = {'Compile T95H kernel and assemble Debian kiosk SD',
                'Assemble eMMC and offline installation SD',
                'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'}
    if not any(required <= {s['name'] for s in job['steps'] if s['conclusion'] == 'success'} for job in jobs):
        raise ValueError('Completed image build and artifact upload not verified')
    return info


def reserve_tag(repo, run, attempt, commit):
    if not run.isdecimal() or not attempt.isdecimal() or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid build identity')
    client = GitHub(repo)
    tag = f'anotter-{run}-{attempt}'
    ref = client.api(f'repos/{repo}/git/ref/tags/{tag}')
    if ref is None:
        ref = client.api(f'repos/{repo}/git/refs', 'POST',
                         dict(ref='refs/tags/' + tag, sha=commit))
    if ref['object']['type'] != 'commit' or ref['object']['sha'] != commit:
        raise ValueError('Release tag does not point at the build commit')
    print('Build commit reserved:', tag, commit, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-run')
    parser.add_argument('--reserve-tag', action='store_true')
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    if args.reserve_tag:
        reserve_tag(os.environ['GH_REPO'], os.environ['GITHUB_RUN_ID'],
                    os.environ['GITHUB_RUN_ATTEMPT'], os.environ['GITHUB_SHA'])
        return
    if not args.source_run or not args.source_run.isdecimal():
        raise ValueError('Invalid source run')
    repo = os.environ['GH_REPO']
    info = source_info(repo, args.source_run)
    directory = args.directory or ROOT / 'build' / ('anotter-publish-' + args.source_run)
    if args.directory is None:
        subprocess.run(['gh', 'run', 'download', args.source_run, '--repo', repo,
                        '--name', 't95h-anotter-sd-experimental', '--dir', str(directory)], check=True)
    assets = verify(directory)
    print('PASS: SD, eMMC and combined installer checksums verified', flush=True)
    # Existing verified tags define the source commit. target_commitish is
    # only used for NEW tags; avoid asking Actions to create an old workflow ref.
    reserve_tag(repo, args.source_run, str(info['run_attempt']), info['head_sha'])
    GitHub(repo).publish(f'anotter-{args.source_run}-{info["run_attempt"]}', assets,
                         'main', 'T95H AnotterKiosk – SD und eMMC',
                         (directory / 'RELEASE-NOTES.md').read_text(), prerelease=True)


if __name__ == '__main__':
    main()
