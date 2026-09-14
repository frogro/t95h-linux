#!/usr/bin/env python3
"""Assemble a native OpenWrt SD candidate; never access a block device."""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

M = 1024 * 1024
PREFIX_HASH = 'd8fe417be041dd9cd7e1677fed52414fb81f066656a447c2367d9b0fcbc94b75'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    parser = argparse.ArgumentParser()
    for name in ('output', 'kernel', 'dtb', 'rootfs', 'host', 'kernel-config'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--release', required=True)
    parser.add_argument('--medium', choices=('sd', 'emmc'), default='sd')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.release):
        raise ValueError('Only a final stable release is permitted; no snapshot fallback')
    config = args.kernel_config.read_text()
    required = {
        'PM_GENERIC_DOMAINS': 'y',
        'PM_GENERIC_DOMAINS_OF': 'y',
        'T95H_GUARDED_POWER_DOMAINS': 'y',
        'ARM_ALLWINNER_SUN50I_CPUFREQ_NVMEM': 'm',
        'DRM_PANFROST': 'm',
        'CPU_FREQ_THERMAL': 'y',
        'DEVFREQ_THERMAL': 'y',
        'DRM_SUN4I': 'm',
        'DRM_SUN8I_MIXER': 'm',
        'VIDEO_SUNXI_CEDRUS': 'm',
        'SND_SUN4I_CODEC': 'm',
        'SND_SOC_SUNXI_AHUB': 'm',
        'IR_SUNXI': 'm',
        'BT_HCIBTUSB': 'm',
    }
    for symbol, value in required.items():
        if f'CONFIG_{symbol}={value}' not in config.splitlines():
            raise ValueError(f'Unsafe/incomplete compute config: {symbol} must be {value}')
    # Image creation must not succeed with the old snapshot root or missing
    # late-start modules, even when the kernel compile itself succeeded.
    def root_file(path):
        result = subprocess.run([str(args.host/'debugfs'), '-R', 'cat '+path,
                                 str(args.rootfs)], capture_output=True, text=True, check=True)
        return result.stdout
    release_text = root_file('/etc/openwrt_release')
    if f"DISTRIB_RELEASE='{args.release}'" not in release_text:
        raise ValueError('Root filesystem version does not match selected stable release')
    feeds = root_file('/etc/apk/repositories.d/distfeeds.list')
    if 'SNAPSHOT' in feeds or f'https://downloads.openwrt.org/releases/{args.release}/' not in feeds:
        raise ValueError('Root filesystem feeds do not match stable release')
    kernel_release = (args.kernel_config.parent/'include/config/kernel.release').read_text().strip()
    for module in ('panfrost', 't95h_ana_provider', 'sun50i-cpufreq-nvmem', 'usbhid',
                   'sun4i-drm', 'sun8i-mixer', 'sun8i-drm-hdmi', 'sunxi-cedrus',
                   'sun4i-codec', 'snd_soc_sunxi_ahub', 'snd_soc_sunxi_machine',
                   'sunxi-cir', 'btusb'):
        result = subprocess.run([str(args.host/'debugfs'), '-R',
                                 f'stat /lib/modules/{kernel_release}/{module}.ko', str(args.rootfs)],
                                capture_output=True, text=True, check=True)
        if 'Inode:' not in result.stdout:
            raise ValueError('Missing runtime module: '+module)

    base = Path(__file__).resolve().parent
    emmc = args.medium == 'emmc'
    prefix_hash = '589a5fff38e1510524f89afd5691e7a8bac3437c42bcd3dddeaaf3d7ff4f9c78' if emmc else PREFIX_HASH
    prefix = base / ('emmc-prefix.bin' if emmc else 'prefix.bin')
    if prefix.stat().st_size != 4*M or sha(prefix) != prefix_hash:
        raise ValueError('T95H boot-prefix hash mismatch')
    data = prefix.read_bytes()
    if data[510:512] != b'\x55\xaa':
        raise ValueError('Missing MBR signature')
    for slot, start, sectors in ((0, 8192, 131072), (1, 139264, 3956736)):
        if struct.unpack_from('<II', data, 446 + slot*16 + 8) != (start, sectors):
            raise ValueError('Partition layout differs from tested boot prefix')
    if data[440:444].hex() != ('01005ee9' if emmc else '4cddbdc5'):
        raise ValueError('Root PARTUUID does not match boot command')
    if args.rootfs.stat().st_size != 1932*M:
        raise ValueError('Set CONFIG_TARGET_ROOTFS_PARTSIZE=1932')
    if not args.kernel.is_file() or not args.dtb.is_file():
        raise ValueError('Missing kernel or DTB')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def run(tool, *values):
        subprocess.run([str(args.host/tool), *map(str, values)], check=True)
    with tempfile.TemporaryDirectory(prefix='t95h-assemble-', dir=args.output.parent) as tmp:
        temp = Path(tmp)
        boot = temp/'boot'
        boot.mkdir()
        shutil.copy2(args.kernel, boot/'Image')
        shutil.copy2(args.dtb, boot/'t95h.dtb')
        shutil.copy2(base/'boot.scr', boot/'boot.scr')
        boot_cmd = temp/'boot.cmd'
        text = (base/'boot.cmd').read_text()
        if emmc:
            text = text.replace('c5bddd4c-02', 'e95e0001-02').replace('T95H: SD', 'T95H: eMMC')
        boot_cmd.write_text(text)
        run('mkimage', '-A', 'arm', '-T', 'script', '-C', 'none', '-n',
            'T95H native OpenWrt', '-d', boot_cmd, boot/'boot.scm')
        fat = temp/'boot.fat'
        with fat.open('wb') as stream:
            stream.truncate(64*M)
        run('mkfs.fat', '--invariant', '-F', '16', '-i', ('E95E0001' if emmc else '54393548'), '-n', 'T95HBOOT', fat)
        run('mcopy', '-s', '-i', fat, boot, '::/')
        run('fsck.fat', '-n', fat)
        # make_ext4fs can leave inode-bitmap padding unset. Repair only this
        # recognized generator defect in a private copy, then require a clean check.
        rootfs = temp/'root.ext4'
        shutil.copyfile(args.rootfs, rootfs)
        check = subprocess.run([str(args.host/'e2fsck'), '-fn', str(rootfs)],
                               capture_output=True, text=True)
        if check.returncode:
            detail = check.stdout + check.stderr
            if check.returncode != 4 or 'Padding at end of inode bitmap is not set.' not in detail:
                raise RuntimeError('Unexpected rootfs validation failure: '+detail)
            repair = subprocess.run([str(args.host/'e2fsck'), '-fy', str(rootfs)],
                                    capture_output=True, text=True)
            (temp/'rootfs-repair.log').write_text(repair.stdout + repair.stderr)
            if repair.returncode not in (0, 1):
                raise RuntimeError('Rootfs bitmap repair failed: '+repair.stdout+repair.stderr)
        if emmc:
            run('tune2fs', '-U', 'e95e0001-0000-4000-8000-000000000002', rootfs)
        run('e2fsck', '-fn', rootfs)
        # The common rootfs contains both guarded upgrade paths.
        upgrade = root_file('/lib/upgrade/platform.sh')
        for expected in (PREFIX_HASH, '589a5fff38e1510524f89afd5691e7a8bac3437c42bcd3dddeaaf3d7ff4f9c78', 'RAMFS_COPY_BIN'):
            if expected not in upgrade:
                raise ValueError('Rootfs lacks dual-media upgrade support: '+expected)
        hashes = {}
        for name in ('Image', 't95h.dtb', 'boot.scr', 'boot.scm'):
            restored = temp/('readback-'+name)
            run('mcopy', '-i', fat, '::/boot/'+name, restored)
            hashes[name] = sha(boot/name)
            if sha(restored) != hashes[name]:
                raise ValueError('FAT readback mismatch: '+name)
        with args.output.open('wb') as out:
            for source in (prefix, fat, rootfs):
                with source.open('rb') as inp:
                    shutil.copyfileobj(inp, out, 1024*1024)
        if args.output.stat().st_size != 2000*M:
            raise ValueError('Unexpected image length')
        report = {'hardware_tested': False, 'full_backport_complete': False,
                  'scope': 'native stable '+args.medium+' candidate with Ethernet/WLAN, USB, IR, front display, CPU/GPU, HDMI, audio and Cedrus',
                  'stable_release': args.release, 'kernel_release': kernel_release,
                  'kernel_and_boot_sha256': hashes, 'medium': args.medium, 'prefix_sha256': prefix_hash,
                  'rootfs_sha256': sha(rootfs), 'raw_image_sha256': sha(args.output)}
        args.output.with_suffix('.manifest.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report))

if __name__ == '__main__':
    main()
