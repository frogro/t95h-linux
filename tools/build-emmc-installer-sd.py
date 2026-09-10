#!/usr/bin/env python3
"""Create compressed three-partition SD installer from verified SD/eMMC builds."""
import argparse,gzip,hashlib,importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];M=1048576

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(*a):return subprocess.check_output(list(map(str,a)),stderr=subprocess.STDOUT)
def main():
 p=argparse.ArgumentParser()
 for n in ['sd-package','emmc-package','host-tools','compiler','output']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.output.resolve();o.mkdir(parents=True,exist_ok=False)
 epoch=int(os.environ['SOURCE_DATE_EPOCH']);os.environ['E2FSPROGS_FAKE_TIME']=str(epoch)
 sd=json.loads((a.sd_package/'build-proof.json').read_text());em=json.loads((a.emmc_package/'build-proof.json').read_text())
 if sd['storage']!='sd' or em['storage']!='emmc' or sd['profile']!=em['profile'] or sd['custom_kernel']!=em['custom_kernel']:raise ValueError('Mismatched package pair')
 for d,pr in [(a.sd_package,sd),(a.emmc_package,em)]:
  if sha(d/pr['sysupgrade'])!=pr['sysupgrade_sha256']:raise ValueError('Upgrade payload hash mismatch')
 prefix=bytearray((a.sd_package/'prefix.bin').read_bytes())
 if len(prefix)!=4*M or sha(a.sd_package/'prefix.bin')!=sd['boot_prefix_sha256']:raise ValueError('SD prefix mismatch')
 if any(prefix[478:510]):raise ValueError('Third/fourth partition already occupied')
 prefix[478:494]=struct.pack('<B3sB3sII',0,b'\0'*3,131,b'\0'*3,4096000,524288)
 (o/'prefix.bin').write_bytes(prefix)
 for file,key in [('root.ext4','rootfs_sha256'),('boot.fat','boot_sha256')]:
  if sha(a.sd_package/file)!=sd[key]:raise ValueError('SD partition hash mismatch')
  shutil.copyfile(a.sd_package/file,o/file)
 fat=o/'boot.fat';fs=o/'root.ext4';host=a.host_tools.resolve()
 run(host/'mcopy','-i',fat,'::/boot/t95h.dtb',o/'before.dtb')
 spec=importlib.util.spec_from_file_location('dt',ROOT/'tools/emmc/prepare-access-dtb.py');dt=importlib.util.module_from_spec(spec);spec.loader.exec_module(dt);dt.prepare(o/'before.dtb',o/'installer.dtb')
 run(host/'mcopy','-o','-i',fat,o/'installer.dtb','::/boot/t95h.dtb')
 src=ROOT/'boards/t95h/emmc-installer'
 for name in ['reread-partitions','check-boot-selection','file-metadata']:
  run(a.compiler,'-Os','-static',src/(name+'.c'),'-o',o/name)
 files=[(src/'t95h-install-emmc','/usr/sbin/t95h-install-emmc'),(src/'check-config','/usr/lib/t95h-emmc/check-config'),(a.emmc_package/'platform.sh','/usr/lib/t95h-emmc/platform.sh')]+[(o/n,'/usr/lib/t95h-emmc/'+n) for n in ['reread-partitions','check-boot-selection','file-metadata']]
 commands=['mkdir /usr/lib/t95h-emmc']
 for source,dest in files:
  commands.extend([f'write {source.resolve()} {dest}',f'set_inode_field {dest} mode 0100755',f'set_inode_field {dest} uid 0',f'set_inode_field {dest} gid 0'])
 (o/'edits.txt').write_text('\n'.join(commands)+'\n');run('debugfs','-w','-f',o/'edits.txt',fs)
 for source,dest in files:
  verify=o/('verify-'+Path(dest).name);run('debugfs','-R',f'dump {dest} {verify}',fs)
  if sha(source)!=sha(verify):raise ValueError('Installer rootfs readback mismatch')
 run('python3',ROOT/'tools/test-emmc-metadata.py',o/'verify-file-metadata')
 payload=o/'payload';payload.mkdir()
 shutil.copyfile(a.emmc_package/em['sysupgrade'],payload/'emmc-sysupgrade.bin')
 shutil.copyfile(a.emmc_package/'prefix.bin',payload/'prefix.bin')
 (payload/'SHA256SUMS').write_text(''.join(sha(payload/n)+'  '+n+'\n' for n in ['emmc-sysupgrade.bin','prefix.bin']))
 part=o/'installer.ext4'
 with part.open('xb') as f:f.truncate(256*M)
 run('mkfs.ext4','-q','-F','-b','4096','-U','95361603-0000-4000-8000-000000000003','-L','T95HINSTALL','-O','^has_journal','-E','lazy_itable_init=0','-d',payload,part)
 for f in [fs,part]:run('e2fsck','-fn',f)
 run(host/'fsck.fat','-n',fat)
 # Read payload back from the third partition, not only the source directory.
 for n in ['emmc-sysupgrade.bin','prefix.bin','SHA256SUMS']:
  v=o/('verify-payload-'+n);run('debugfs','-R',f'dump /{n} {v}',part)
  if sha(v)!=sha(payload/n):raise ValueError('Installer payload readback mismatch')
 name=sd['install_image'].removesuffix('-sd-install.img')+'-sd-emmc-installer.img.gz'
 h=hashlib.sha256();count=0
 with (o/name).open('xb') as dest,gzip.GzipFile(fileobj=dest,mode='wb',filename='',mtime=epoch,compresslevel=6) as gz:
  for n in ['prefix.bin','boot.fat','root.ext4','installer.ext4']:
   with (o/n).open('rb') as f:
    while data:=f.read(M):h.update(data);count+=len(data);gz.write(data)
 with gzip.open(o/name,'rb') as f:
  if hashlib.file_digest(f,'sha256').hexdigest()!=h.hexdigest():raise ValueError('Compressed installer readback mismatch')
 if count!=2256*M:raise ValueError('Installer size mismatch')
 report=dict(image=name,sha256=sha(o/name),raw_sha256=h.hexdigest(),raw_bytes=count,third_partition_start=4096000,third_partition_sectors=524288,profile=sd['profile'],emmc_sysupgrade_sha256=em['sysupgrade_sha256'],payload_readback_verified=True,metadata_helper_runtime_verified=True,hardware_install_tested=False)
 (o/'installer-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
