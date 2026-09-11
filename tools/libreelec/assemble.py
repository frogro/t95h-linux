#!/usr/bin/env python3
"""Assemble experimental SD/eMMC media from LE-built KERNEL and SYSTEM, no devices."""
import argparse,gzip,hashlib,importlib.util,json,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];M=1048576

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(*args):subprocess.run(list(map(str,args)),check=True)
def built_kernel_config(le, version):
 # LibreELEC retains the actual built config even when its source is autoremoved.
 builds=list(le.glob('build.LibreELEC-T95H.aarch64-*'))
 candidates=[]
 for build in builds:
  installed=build/'install_pkg'/('linux-'+version)/'.image/.config'
  source=build/'build'/('linux-'+version)/'.config'
  existing=[p for p in (installed,source) if p.is_file()]
  if len(existing)==2 and installed.read_bytes()!=source.read_bytes():
   raise ValueError('Built and installed kernel configs disagree: '+str(build))
  if existing:candidates.append(existing[0])
 if len(candidates)!=1:
  raise ValueError('Expected one built kernel config; found '+repr([str(p) for p in candidates]))
 return candidates[0]

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 le=a.source.resolve();version=json.loads((le/'t95h-port.json').read_text())['upstream']['tag'];o=a.output.resolve();o.mkdir(parents=True,exist_ok=False)
 port=json.loads((le/'t95h-port.json').read_text())
 config=built_kernel_config(le,port['kernel'])
 print('Checking built kernel config:',config)
 lines=set(config.read_text().splitlines())
 missing=[k for k in port['required_kernel_config'] if not ({'CONFIG_'+k+'=y','CONFIG_'+k+'=m'} & lines)]
 if missing:raise ValueError('LibreELEC kernel requirements missing: '+repr(missing))
 kernels=list((le/'target').glob('*.kernel'));systems=list((le/'target').glob('*.system'))
 if len(kernels)!=1 or len(systems)!=1:raise ValueError('Expected one LE kernel/system pair')
 lock=json.loads((ROOT/'boards/t95h/build-inputs.json').read_text());prefix=a.prefix.read_bytes()
 if len(prefix)!=4*M or sha(a.prefix)!=lock['boot_prefix_sha256']:raise ValueError('Bootprefix mismatch')
 dtb=le/'t95h-startup/t95h.dtb';reports={}
 for media in ('sd','emmc'):
  d=o/media;d.mkdir();original=prefix
  if media=='emmc':
   # The exact eMMC prefix transformation is provided by the existing checked helper.
   # See CLI below; no hardware tool is invoked.
   run('python3',ROOT/'tools/emmc/prepare-boot-prefix.py','--source',a.prefix,'--output',d/'emmc-prefix.bin')
   original=(d/'emmc-prefix.bin').read_bytes()
  b=bytearray(original);b[440:444]=struct.pack('<I',0x1e950001 if media=='sd' else 0x1e950002)
  b[446:510]=b'\0'*64
  b[446:462]=struct.pack('<B3sB3sII',0,b'\0'*3,12,b'\0'*3,8192,2097152)
  b[462:478]=struct.pack('<B3sB3sII',0,b'\0'*3,131,b'\0'*3,2105344,1048576)
  assert b[512:]==original[512:];(d/'prefix.bin').write_bytes(b)
  fat=d/'boot.fat';storage=d/'storage.ext4'
  with fat.open('wb') as f:f.truncate(1024*M)
  with storage.open('wb') as f:f.truncate(512*M)
  bootid='1E950001' if media=='sd' else '1E950002';rootid='1e950001-0000-4000-8000-000000000002' if media=='sd' else '1e950002-0000-4000-8000-000000000002'
  run('mkfs.vfat','-F','32','-i',bootid,'-n','LIBREELEC',fat);run('mkfs.ext4','-F','-L','STORAGE','-U',rootid,storage)
  chosen=dtb
  if media=='emmc':
   spec=importlib.util.spec_from_file_location('dt',ROOT/'tools/emmc/prepare-access-dtb.py');dt=importlib.util.module_from_spec(spec);spec.loader.exec_module(dt);chosen=d/'t95h.dtb';dt.prepare(dtb,chosen)
  text=(ROOT/'boards/t95h/boot/scripts/boot.scm.txt').read_text()
  start=text.index('setenv bootargs ');end=text.index('\n',start)
  text=text[:start]+f'setenv bootargs console=ttyS0,115200 console=tty0 earlycon=uart8250,mmio32,0x05000000 loglevel=7 boot=UUID={bootid[:4]}-{bootid[4:]} disk=UUID={rootid} quiet ssh net.ifnames=0'+text[end:]
  # Use the same filename for boot and future LE update payloads.
  text=text.replace('/boot/Image','/KERNEL');(d/'boot.scm.txt').write_text(text)
  run('mkimage','-A','arm64','-T','script','-C','none','-n','T95H LibreELEC','-d',d/'boot.scm.txt',d/'boot.scm')
  run('mmd','-i',fat,'::/boot')
  files=[(systems[0],'SYSTEM'),(kernels[0],'KERNEL'),(chosen,'boot/t95h.dtb'),(d/'boot.scm','boot/boot.scm'),(ROOT/'boards/t95h/boot/scripts/boot.scr','boot/boot.scr'),(ROOT/'boards/t95h/boot/scripts/boot.scr','boot.scr')]
  for src,dest in files:
   run('mcopy','-i',fat,src,'::/'+dest);v=d/('verify-'+dest.replace('/','-'));run('mcopy','-i',fat,'::/'+dest,v)
   if sha(v)!=sha(src):raise ValueError('FAT payload mismatch')
  run('fsck.vfat','-n',fat);run('e2fsck','-fn',storage)
  name=f'T95H-LibreELEC-{version}-base-B-{media}.img.gz';h=hashlib.sha256()
  with (o/name).open('wb') as dst,gzip.GzipFile(fileobj=dst,mode='wb',mtime=lock['epoch'],filename='') as gz:
   for part in (d/'prefix.bin',fat,storage):
    with part.open('rb') as src:
     while data:=src.read(M):h.update(data);gz.write(data)
  with gzip.open(o/name,'rb') as src:
   if hashlib.file_digest(src,'sha256').hexdigest()!=h.hexdigest():raise ValueError('Compressed image mismatch')
  reports[media]={'file':name,'sha256':sha(o/name),'raw_sha256':h.hexdigest(),'hardware_tested':False}
 sd=o/reports['sd']['file'];emmc=o/reports['emmc']['file']
 run('python3',ROOT/'tools/build-media-installer.py','--sd',sd,'--emmc',emmc,'--os','libreelec','--output',o/'installer-sd')
 ins=json.loads((o/'installer-sd/installer.json').read_text())
 shutil.copyfile(o/'installer-sd'/ins['file'],o/ins['file'])
 reports['sd_emmc_installer']=ins
 (o/'images.json').write_text(json.dumps(reports,indent=2)+'\n');(o/'SHA256SUMS').write_text(''.join(v['sha256']+'  '+v['file']+'\n' for v in reports.values()))
 print('PASS: experimental SD/eMMC images assembled; hardware test and OS update adapter pending')
if __name__=='__main__':main()
