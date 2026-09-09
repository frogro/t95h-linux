#!/usr/bin/env python3
"""Build locked external drivers against a completed profile kernel; stage all modules."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel-build', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--epoch', type=int, required=True)
    parser.add_argument('--jobs', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 64:
        raise ValueError('Invalid job count')
    kernel = args.kernel_build.resolve(strict=True)
    proof = json.loads((kernel / 'build-status.json').read_text())
    if proof['stage'] != 'kernel-complete':
        raise ValueError('Kernel compilation is not complete; nothing staged')
    for relative, field in [('arch/arm64/boot/Image', 'image_sha256'), ('.config', 'config_sha256')]:
        if sha(kernel / relative) != proof[field]:
            raise ValueError('Kernel output changed: ' + relative)
    tc = args.toolchain.resolve(strict=True)
    prefix = str(tc / 'bin/aarch64-openwrt-linux-musl-')
    if sha(Path(prefix + 'gcc')) != proof['compiler_sha256']:
        raise ValueError('Compiler differs from kernel build')
    board = ROOT / 'boards/t95h/external'
    lock = json.loads((board / 'source-lock.json').read_text())
    for relative, item in lock['files'].items():
        if sha(board / relative) != item['source_sha256']:
            raise ValueError('External source changed: ' + relative)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PATH=str(tc / 'bin') + ':' + os.environ['PATH'],
               STAGING_DIR=str(tc), LC_ALL='C', TZ='UTC', SOURCE_DATE_EPOCH=str(args.epoch),
               KBUILD_BUILD_TIMESTAMP=datetime.datetime.fromtimestamp(args.epoch, datetime.timezone.utc).strftime('%a %b %d %H:%M:%S UTC %Y'),
               KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='t95h', KBUILD_BUILD_VERSION='1')
    profile = proof['profile']
    subprocess.run(['/usr/bin/python3', str(ROOT / 'tools/stage-startup-fixes.py'),
                    '--profile', profile, '--output', str(output / 'startup')], check=True)
    modules = ['regulator']
    shutil.copytree(board / 'regulator', output / 'regulator')
    if 'B' in profile.split('-'):
        shutil.copytree(output / 'startup/ana', output / 'ana')
        modules.append('ana')
    release = (kernel / 'include/config/kernel.release').read_text().strip()
    if not release or '/' in release:
        raise ValueError('Invalid kernel release')
    command = ['make', '-C', str(kernel), 'ARCH=arm64', 'CROSS_COMPILE=' + prefix]
    payload = output / 'root'
    with (output / 'build.log').open('w') as log:
        def run(parts):
            subprocess.run(command + parts, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        run(['INSTALL_MOD_PATH=' + str(payload), 'DEPMOD=true', 'modules_install'])
        for module in modules:
            run(['M=' + str(output / module), '-j' + str(args.jobs), 'modules'])
            run(['M=' + str(output / module), 'INSTALL_MOD_PATH=' + str(payload),
                 'DEPMOD=true', 'modules_install'])
    directory = payload / 'lib/modules' / release
    for name in ['build', 'source']:
        link = directory / name
        if link.is_symlink():
            link.unlink()
    required = ['t95h_aldo2.ko'] + (['t95h_ana_provider.ko'] if 'ana' in modules else [])
    for name in required:
        if len(list(directory.rglob(name))) != 1:
            raise ValueError('External module missing or duplicated: ' + name)
    files = {}
    for path in sorted(directory.rglob('*.ko')):
        vermagic = subprocess.check_output(['modinfo', '-F', 'vermagic', str(path)], text=True).strip()
        if vermagic.split()[0] != release:
            raise ValueError('Module release differs: ' + str(path))
        files[str(path.relative_to(payload))] = {'sha256': sha(path), 'vermagic': vermagic}
    if not files:
        raise ValueError('No modules installed')
    subprocess.run(['depmod', '-b', str(payload), release], check=True)
    report = {'profile': profile, 'kernel_release': release,
              'kernel_image_sha256': proof['image_sha256'], 'config_sha256': proof['config_sha256'],
              'external_drivers': modules, 'modules': files, 'passed': True,
              'kernel_package_ready': False}
    (output / 'modules-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS:', len(files), 'matching modules staged; no APK or image yet')

if __name__ == '__main__':
    main()
