#!/usr/bin/env python3
"""Replay pinned DI300 patches into a NEW review overlay, never a live tree."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
BASE = (
    'drivers/media/platform/sunxi/Kconfig',
    'drivers/media/platform/sunxi/Makefile',
    'arch/arm64/boot/dts/allwinner/sun50i-h616.dtsi',
)


def prepare(source, output, version, driver_only=False):
    source, output = Path(source).resolve(), Path(output).absolute()
    if output.exists():
        raise ValueError('Output already exists; refusing to overwrite')
    if output == source or source in output.parents:
        raise ValueError('Output must be outside the source tree')
    manifest = json.loads((HERE / 'manifest.json').read_text())
    patches = [item for item in manifest['series']
               if not (driver_only and item['commit'] ==
                       '7c3bec1204dfae17ad1bc9cb476e6d84e71b2768')]
    if version == '6.12':
        patches.append(manifest['compat_6_12'])
    for item in patches:
        data = (HERE / item['file']).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Patch checksum mismatch: ' + item['file'])
    # Only the baseline files touched by the series are copied. The output is
    # deliberately NOT a complete kernel and cannot accidentally be booted.
    with tempfile.TemporaryDirectory(prefix='di300-review-') as temp:
        stage = Path(temp)
        for name in BASE[:2] if driver_only else BASE:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        for item in patches:
            subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1',
                            '-i', str(HERE / item['file'])], cwd=stage, check=True)
        shutil.copytree(stage, output)
    print('Review overlay only:', output)
    print('No config enabled, no DTB installed, no runtime module loaded.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--kernel-api', choices=('6.12', '7.2'), required=True)
    parser.add_argument('--driver-only', action='store_true',
                        help='Exclude DT changes; board integration remains unverified')
    args = parser.parse_args()
    prepare(args.source, args.output, args.kernel_api, args.driver_only)
