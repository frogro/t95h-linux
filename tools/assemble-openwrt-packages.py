#!/usr/bin/env python3
"""Build a fresh package root from signed APKs, without an older image or device.

This is the package stage, not a bootable rootfs: postinstall, board runtime,
firmware and image creation remain separate steps.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ARCH = 'aarch64_cortex-a53'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def repositories(version):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Only a resolved stable OpenWrt version is accepted')
    base = 'https://downloads.openwrt.org/releases/' + version
    return [base + '/targets/sunxi/cortexa53/packages/packages.adb'] + [
        base + '/packages/' + ARCH + '/' + feed + '/packages.adb'
        for feed in ('base', 'luci', 'packages', 'routing', 'telephony', 'video')
    ]


def installed_packages(db):
    result = []
    for section in db.split('\n\n'):
        fields = {}
        for line in section.splitlines():
            if line.startswith(('P:', 'V:', 'A:')):
                fields[line[0]] = line[2:]
        if 'P' not in fields:
            continue
        name = fields['P']
        if name == 'kernel' or name.startswith('kmod-'):
            raise ValueError('Official kernel/module package unexpectedly installed: ' + name)
        result.append({'name': name, 'version': fields['V'], 'arch': fields.get('A')})
    if not any(item['name'] == 't95h-kernel' for item in result):
        raise ValueError('Actual custom kernel package missing')
    return sorted(result, key=lambda item: item['name'])


def main():
    from base_module_contract import load as load_base_contract
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--imagebuilder', required=True, type=Path)
    parser.add_argument('--keys', required=True, type=Path)
    parser.add_argument('--kernel-package', required=True, type=Path)
    parser.add_argument('--kernel-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    repo_urls = repositories(request['openwrt'])
    profiles = {'base': ['base'], 'base-A': ['base', 'A'],
                'base-B': ['base', 'B'], 'base-A-B': ['base', 'A', 'B']}
    groups = profiles[request['profile']]
    seeds = json.loads((ROOT/'boards/t95h/openwrt/packages.json').read_text())['seeds']
    packages = sorted({name for group in groups for name in seeds[group]} - {'t95h-kernel'})
    # Exercise the real APK solver with every new kmod name. Official kernel
    # repositories are excluded, so only our verified bundled providers qualify.
    base_kmods = ['kmod-' + name for name in load_base_contract()['providers']]
    packages = sorted(set(packages) | set(base_kmods))
    kernel = args.kernel_package.resolve(strict=True)
    if sha(kernel) != args.kernel_sha256:
        raise ValueError('Custom kernel package checksum mismatch')
    ib = args.imagebuilder.resolve(strict=True)
    if 'openwrt-imagebuilder-' + request['openwrt'] + '-sunxi-cortexa53.' not in ib.name:
        raise ValueError('ImageBuilder does not match resolved release/target')
    apk = ib/'staging_dir/host/bin/apk'
    if not apk.is_file():
        raise ValueError('ImageBuilder host apk missing')
    keys = list(args.keys.glob('*'))
    if not keys or any(not p.is_file() or b'PRIVATE KEY' in p.read_bytes() for p in keys):
        raise ValueError('Only public verification keys may be supplied')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out/'root').mkdir()
    (out/'tmp').mkdir()
    (out/'keys').mkdir()
    for key in keys:
        shutil.copyfile(key, out/'keys'/key.name)
    (out/'repositories').write_text('\n'.join(repo_urls)+'\n')
    shutil.copyfile(args.request, out/'request.json')
    env = dict(os.environ, TMPDIR=str(out/'tmp'), LC_ALL='C', TZ='UTC',
               STAGING_DIR_HOST=str(ib/'staging_dir/host'))
    command = [str(apk), '--root', str(out/'root'), '--keys-dir', str(out/'keys'),
               '--repositories-file', str(out/'repositories'), '--arch', ARCH,
               '--no-logfile', '--no-cache', 'add', '--initdb', '--usermode',
               '--no-scripts', str(kernel), *packages]
    print('Fresh signed package installation; log:', out/'packages.log', flush=True)
    with (out/'packages.log').open('w') as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    resolved = installed_packages((out/'root/lib/apk/db/installed').read_text())
    if sha(kernel) != args.kernel_sha256:
        raise ValueError('Custom kernel package changed while installing')
    report = {'package_stage_passed': True, 'bootable_rootfs_ready': False,
              'previous_image_used': False, 'scripts_executed': False,
              'profile': request['profile'], 'openwrt': request['openwrt'],
              'kernel_package_sha256': args.kernel_sha256,
              'host_apk_sha256': sha(apk), 'requested': packages,
              'verification_keys': {p.name: sha(p) for p in (out/'keys').iterdir()},
              'repositories': repo_urls, 'resolved_packages': resolved,
              'remaining': ['Postinstall and service setup', 'Board runtime and firmware',
                            'Confirm selected kernel source/config matches profile',
                            'Generate install/sysupgrade images']}
    (out/'package-lock.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS: signed fresh package root;', len(resolved), 'packages. Not a bootable image.')


if __name__ == '__main__':
    main()
