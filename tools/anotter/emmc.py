#!/usr/bin/env python3
"""Derive Anotter eMMC and installer SD from the same completed SD build."""
import argparse,gzip,hashlib,json,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];M=1048576

def run(*a):subprocess.run(list(map(str,a)),check=True)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);a=p.parse_args();b=a.build.resolve();release=b/'release'
 m=json.loads((release/'manifest.json').read_text());sd=release/m['image']
 if sha(sd)!=m['sha256']:raise ValueError('SD image changed')
 d=b/'emmc';d.mkdir()
 run('python3',ROOT/'tools/emmc/prepare-boot-prefix.py','--source',b/'inputs/prefix.bin','--output',d/'prefix.bin')
 # Keep partition starts/sizes but distinguish SD and eMMC PARTUUIDs.
 with gzip.open(sd,'rb') as f:sd_prefix=f.read(4*M)
 prefix=bytearray((d/'prefix.bin').read_bytes());prefix[440:444]=struct.pack('<I',0xa0950002);prefix[446:510]=sd_prefix[446:510];(d/'prefix.bin').write_bytes(prefix)
 shutil.copyfile(b/'boot.fat',d/'boot.fat');shutil.copyfile(b/'root.ext4',d/'root.ext4')
 fat=d/'boot.fat';fs=d/'root.ext4'
 run('mlabel','-i',fat,'-N','a0950002','::T95HKIOSK')
 run('python3',ROOT/'tools/emmc/prepare-access-dtb.py','--source',b/'modules/startup/t95h.dtb','--output',d/'t95h.dtb')
 run('mcopy','-o','-i',fat,d/'t95h.dtb','::/boot/t95h.dtb')
 text=(b/'boot.txt').read_text()
 if text.count('root=PARTUUID=a0950001-02')!=1:raise ValueError('Root argument contract changed')
 (d/'boot.txt').write_text(text.replace('root=PARTUUID=a0950001-02','root=PARTUUID=a0950002-02'))
 run('mkimage','-A','arm64','-T','script','-C','none','-n','T95H Anotter eMMC','-d',d/'boot.txt',d/'boot.scm')
 run('mcopy','-o','-i',fat,d/'boot.scm','::/boot/boot.scm')
 run('debugfs','-R',f'dump /etc/fstab {d}/fstab',fs)
 f=(d/'fstab').read_text()
 if 'a0950001-02' not in f or 'a0950001-01' not in f:raise ValueError('fstab contract changed')
 (d/'fstab').write_text(f.replace('a0950001-','a0950002-'))
 (d/'edits').write_text(f'rm /etc/fstab\nwrite {d}/fstab /etc/fstab\nset_inode_field /etc/fstab mode 0100644\nset_inode_field /etc/fstab uid 0\nset_inode_field /etc/fstab gid 0\n')
 run('debugfs','-w','-f',d/'edits',fs)
 run('debugfs','-R',f'dump /etc/fstab {d}/fstab-check',fs)
 if sha(d/'fstab')!=sha(d/'fstab-check'):raise ValueError('fstab readback mismatch')
 run('tune2fs','-U','a0950002-0000-4000-8000-000000000002',fs)
 run('e2fsck','-fn',fs);run('fsck.vfat','-n',fat)
 name=sd.name.replace('-sd.img.gz','-emmc.img.gz');target=release/name;h=hashlib.sha256()
 with target.open('xb') as dst,gzip.GzipFile(fileobj=dst,mode='wb',filename='',mtime=0,compresslevel=3) as z:
  for src in (d/'prefix.bin',fat,fs):
   with src.open('rb') as f:
    while data:=f.read(M):h.update(data);z.write(data)
 with gzip.open(target,'rb') as f:
  if hashlib.file_digest(f,'sha256').hexdigest()!=h.hexdigest():raise ValueError('eMMC compression mismatch')
 run('python3',ROOT/'tools/build-media-installer.py','--sd',sd,'--emmc',target,'--os','anotter','--output',b/'installer-sd')
 ins=json.loads((b/'installer-sd/installer.json').read_text());shutil.copyfile(b/'installer-sd'/ins['file'],release/ins['file'])
 shutil.copyfile(b/'installer-sd/installer.json',release/'installer.json')
 m['emmc']={'file':name,'sha256':sha(target),'raw_sha256':h.hexdigest(),'hardware_install_tested':False};m['sd_emmc_installer']=ins
 (release/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (release/'SHA256SUMS').open('a') as f:f.write(sha(target)+'  '+name+'\n'+ins['sha256']+'  '+ins['file']+'\n')
if __name__=='__main__':main()
