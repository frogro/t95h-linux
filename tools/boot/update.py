#!/usr/bin/env python3
"""Offline boot-only update for an unmounted T95H SD/eMMC or raw image.
Default is read-only. Never modifies partition table, rootfs or later firmware.
"""
import argparse, fcntl, hashlib, json, os, stat, struct, subprocess, tempfile, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'boards/t95h/boot/pmic305'
M=1048576
sha=lambda b:hashlib.sha256(b).hexdigest()
def clean_script(blob):
    if len(blob)<72 or struct.unpack_from('>I',blob)[0]!=0x27051956:
        raise ValueError('Not a legacy U-Boot script')
    h=bytearray(blob[:64]);crc=struct.unpack_from('>I',h,4)[0];struct.pack_into('>I',h,4,0)
    data=blob[64:]
    if zlib.crc32(h)!=crc or zlib.crc32(data)!=struct.unpack_from('>I',h,24)[0] or len(data)!=struct.unpack_from('>I',h,12)[0]:
        raise ValueError('Boot script CRC/length mismatch')
    text=data[8:].decode()
    if 'while true; do sleep 60; done' in text:
        text=text.replace('three SD attempts failed; stopped','three SD attempts failed; returning to U-Boot').replace('while true; do sleep 60; done','false')
    # Preserve OS-specific kernel/root arguments; never install a different OS script.
    if 't95h-diag-init' in text:
        raise ValueError('Historical diagnostic OpenWrt script: outside kernel6 scope')
    data=struct.pack('>II',len(text.encode()),0)+text.encode()
    struct.pack_into('>I',h,12,len(data));struct.pack_into('>I',h,24,zlib.crc32(data));struct.pack_into('>I',h,4,zlib.crc32(h))
    return bytes(h)+data

def corrected_prefix(old, medium):
    lock=json.loads((ASSETS/'lock.json').read_text())[medium]
    if len(old)!=4*M or sha(old[512:]) not in (lock['legacy_firmware_region_sha256'],lock['firmware_region_sha256']):
        raise ValueError('Unknown or wrong-medium boot firmware')
    spl=(ASSETS/(medium+'.toc0')).read_bytes()
    if len(spl)!=40960 or sha(spl)!=lock['spl_sha256']:raise ValueError('SPL hash mismatch')
    new=bytearray(old);new[8192:49152]=spl
    return bytes(new)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('device',type=Path);p.add_argument('--medium',choices=['sd','emmc'],required=True)
    p.add_argument('--backup',type=Path);p.add_argument('--apply',action='store_true')
    p.add_argument('--image',action='store_true',help='Permit a regular raw image for offline validation')
    a=p.parse_args();dev=a.device.resolve();st=dev.stat()
    if stat.S_ISBLK(st.st_mode):
        base=Path('/sys/class/block')/dev.name
        if (base/'partition').exists():raise ValueError('Whole disk required')
        if any((base/'holders').iterdir()):raise ValueError('Target has active holders')
        nums={(base/'dev').read_text().strip()}
        nums.update(f.read_text().strip() for f in base.glob(dev.name+'*/dev'))
        if any(line.split()[2] in nums for line in Path('/proc/self/mountinfo').read_text().splitlines()):
            raise ValueError('Unmount all target partitions first')
        if any(str(dev) in l for l in Path('/proc/swaps').read_text().splitlines()[1:]):raise ValueError('Target swap is active')
    elif not (a.image and stat.S_ISREG(st.st_mode)):raise ValueError('Block device required, or --image for a raw file')
    with dev.open('r+b' if a.apply else 'rb',buffering=0) as disk:
        fcntl.flock(disk,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=disk.read(4*M);new=corrected_prefix(old,a.medium)
        start,count=struct.unpack_from('<II',old,454)
        if start!=8192 or count not in (131072,262144,2097152):raise ValueError('Unknown FAT layout')
        disk.seek(start*512);fat=disk.read(count*512)
        if len(fat)!=count*512:raise ValueError('Truncated FAT')
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);image=d/'boot.fat';image.write_bytes(fat)
            script=d/'boot.scm'
            subprocess.run(['mcopy','-i',str(image),'::/boot/boot.scm',str(script)],check=True)
            before=script.read_bytes();after=clean_script(before);script.write_bytes(after)
            subprocess.run(['mcopy','-o','-i',str(image),str(script),'::/boot/boot.scm'],check=True)
            subprocess.run(['fsck.fat','-n',str(image)],check=True,stdout=subprocess.DEVNULL)
            updated=image.read_bytes()
        report={'medium':a.medium,'device':str(dev),'spl_changed':old[8192:49152]!=new[8192:49152],'script_changed':before!=after,'applied':False}
        if a.apply:
            if not a.backup:raise ValueError('--backup directory required for --apply')
            a.backup.mkdir(parents=True,exist_ok=False)
            for name,data in [('prefix.bin',old),('boot.fat',fat)]:
                with (a.backup/name).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
            disk.seek(0)
            if disk.read(4*M)!=old:raise ValueError('Firmware changed during preparation')
            try:
                disk.seek(start*512);disk.write(updated);os.fsync(disk.fileno())
                disk.seek(8192);disk.write(new[8192:49152]);os.fsync(disk.fileno())
                disk.seek(0)
                if disk.read(4*M)!=new:raise IOError('Firmware readback mismatch')
                disk.seek(start*512)
                if disk.read(len(updated))!=updated:raise IOError('FAT readback mismatch')
            except BaseException:
                disk.seek(8192);disk.write(old[8192:49152]);disk.seek(start*512);disk.write(fat);os.fsync(disk.fileno());raise
            report['applied']=True
            (a.backup/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
if __name__=='__main__':main()
