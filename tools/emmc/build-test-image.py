#!/usr/bin/env python3
"""Derive experimental eMMC image from a verified SD release. No device writes."""
import argparse,hashlib,importlib.util,json,os,struct,subprocess
from pathlib import Path
import libfdt
ROOT=Path(__file__).resolve().parents[2]
M=1048576

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(*cmd):return subprocess.check_output([str(x) for x in cmd],stderr=subprocess.STDOUT)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ['image','prefix','host-tools','output']:p.add_argument('--'+key,required=True,type=Path)
 p.add_argument('--sha256',required=True);a=p.parse_args()
 if a.image.stat().st_size!=2000*M or sha(a.image)!=a.sha256:raise ValueError('Input image hash/size mismatch')
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 spec=importlib.util.spec_from_file_location('prefix_builder',Path(__file__).with_name('prepare-boot-prefix.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 mod.prepare(a.prefix,out/'prefix.bin')
 with a.image.open('rb') as source:
  for name,start,size in [('boot.fat',4*M,64*M),('root.ext4',68*M,1932*M)]:
   source.seek(start)
   with (out/name).open('xb') as dest:
    for _ in range(size//M):
     b=source.read(M)
     if len(b)!=M:raise ValueError('Short source read')
     dest.write(b)
    dest.flush();os.fsync(dest.fileno())
 fat=out/'boot.fat';fs=out/'root.ext4';mcopy=a.host_tools/'mcopy'
 for name in ['t95h.dtb','boot.scm','boot.scr']:
  run(mcopy,'-i',fat,'::/boot/'+name,out/('old-'+name))
 spec=importlib.util.spec_from_file_location('access_dtb',Path(__file__).with_name('prepare-access-dtb.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 report=mod.prepare(out/'old-t95h.dtb',out/'t95h.dtb')
 for name in ['boot.scm','boot.scr']:
  b=(out/('old-'+name)).read_bytes()
  if b[:4]!=bytes.fromhex('27051956'):raise ValueError('Unexpected script image')
  text=b[72:].decode().replace('c5bddd4c-02','e95e0001-02').replace('T95H: SD','T95H: eMMC').replace('three SD','three eMMC')
  (out/(name+'.txt')).write_text(text)
  run('mkimage','-A','arm64','-O','linux','-T','script','-C','none','-n','T95H eMMC experimental','-d',out/(name+'.txt'),out/name)
 for name in ['t95h.dtb','boot.scm','boot.scr']:run(mcopy,'-o','-i',fat,out/name,'::/boot/'+name)
 # FAT16 volume serial at byte 39; this is the locked 64 MiB FAT16 layout.
 with fat.open('r+b') as f:
  head=f.read(512)
  if head[54:62]!=b'FAT16   ':raise ValueError('Expected FAT16')
  f.seek(39);f.write(struct.pack('<I',0xe95e0001));f.flush();os.fsync(f.fileno())
 fstab=out/'fstab';fstab.write_text("config global\n option auto_mount '1'\n option anon_mount '0'\n option auto_swap '0'\n option anon_swap '0'\n\nconfig mount\n option target '/boot'\n option uuid 'E95E-0001'\n option fstype 'vfat'\n option options 'rw,noatime'\n option enabled '1'\n")
 platform=Path(__file__).resolve().parents[2]/'boards/t95h/openwrt/upgrade/platform.sh'
 edits=[]
 for src,dest,mode in [(fstab,'/etc/config/fstab','0100644'),(platform,'/lib/upgrade/platform.sh','0100755')]:
  edits += ['rm '+dest,f'write {src} {dest}',f'set_inode_field {dest} mode {mode}',f'set_inode_field {dest} uid 0',f'set_inode_field {dest} gid 0']
 (out/'edits.txt').write_text('\n'.join(edits)+'\n')
 (out/'debugfs.log').write_bytes(run('debugfs','-w','-f',out/'edits.txt',fs))
 run('tune2fs','-U','e95e0001-0000-4000-8000-000000000002',fs)
 (out/'e2fsck.log').write_bytes(run('e2fsck','-fn',fs));(out/'fat-check.log').write_bytes(run(a.host_tools/'fsck.fat','-n',fat))
 for name in ['t95h.dtb','boot.scm','boot.scr']:
  run(mcopy,'-i',fat,'::/boot/'+name,out/('verify-'+name))
  if sha(out/('verify-'+name))!=sha(out/name):raise ValueError('FAT payload readback mismatch')
 for dest in ['etc/config/fstab','lib/upgrade/platform.sh']:
  verify=out/('verify-'+Path(dest).name);run('debugfs','-R',f'dump /{dest} {verify}',fs)
  if verify.read_bytes()!=(fstab if dest.endswith('fstab') else platform).read_bytes():raise ValueError('Root configuration readback mismatch')
 image=out/'t95h-emmc-test.img'
 with image.open('xb') as f:
  for name in ['prefix.bin','boot.fat','root.ext4']:
   with (out/name).open('rb') as s:
    while b:=s.read(M):f.write(b)
  f.flush();os.fsync(f.fileno())
 assert image.stat().st_size==2000*M
 report.update(image_sha256=sha(image),source_image_sha256=a.sha256,bytes=image.stat().st_size,emmc_hardware_boot_tested=False,sysupgrade_enabled=True,contains_device_keys=False)
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
