#!/usr/bin/env python3
"""Derive matching T95H install + sysupgrade artifacts from a locked, verified image.
No kernel build, network access, host paths embedded in artifacts, or device writes.
Requires Python 3.11+, e2fsprogs and OpenWrt fwtool. SOURCE_DATE_EPOCH required.
"""
import argparse, gzip, hashlib, io, json, os, re, shutil, struct, subprocess, tarfile, mmap
from pathlib import Path
M=1048576; SIZE=2000*M

def direct_chunks(p,start=0,size=None):
 size=p.stat().st_size-start if size is None else size
 fd=os.open(p,os.O_RDONLY|os.O_DIRECT);buf=mmap.mmap(-1,M)
 try:
  for off in range(0,size,M):
   n=os.preadv(fd,[buf],start+off);want=min(M,size-off)
   if n < want:raise RuntimeError('Short direct read: '+str(p))
   yield buf[:want]
 finally:buf.close();os.close(fd)
def sha(p):
 h=hashlib.sha256()
 for data in direct_chunks(p):h.update(data)
 return h.hexdigest()
def flush(p):
 with p.open('rb') as f:
  os.fsync(f.fileno());os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
def run(*args):
 r=subprocess.run(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=dict(os.environ,LC_ALL='C',TZ='UTC',E2FSPROGS_FAKE_TIME=str(E)))
 if r.returncode:raise RuntimeError(r.stdout.decode(errors='replace'))
 return r.stdout

def extract(src,dst,start,size):
 h=hashlib.sha256()
 # Avoid buffered copy writes; all partition extents are MiB aligned.
 assert size % M == 0 and start % M == 0
 fd=os.open(dst,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_DIRECT,0o600)
 buf=mmap.mmap(-1,M)
 try:
  for data in direct_chunks(src,start,size):
   buf[:]=data
   if os.write(fd,buf)!=len(data):raise RuntimeError('Short direct write')
   h.update(data)
  os.fsync(fd)
 finally:buf.close();os.close(fd)
 flush(dst)
 if sha(dst)!=h.hexdigest():raise RuntimeError('Extracted region verification failed')
 # Independent re-read of source region.
 h2=hashlib.sha256()
 for data in direct_chunks(src,start,size):h2.update(data)
 if h2.hexdigest()!=h.hexdigest():raise RuntimeError('Source region changed during copy')
def gz(src,dst):
 with dst.open('wb') as out,gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0,compresslevel=9) as g:
  for data in direct_chunks(src):g.write(data)
 flush(dst)
def dump(fs,name,out):
 run('debugfs','-R',f'dump {name} {out}',fs)
 if not out.exists():raise RuntimeError('Missing image file: '+name)

p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--fwtool',type=Path,required=True)
p.add_argument('--platform',type=Path,help='Explicit validated platform hook; default is repository hook')
p.add_argument('--storage',choices=['sd','emmc'],default='sd')
p.add_argument('--profile',choices=['base','base-A','base-B','base-A-B'])
a=p.parse_args();E=int(os.environ['SOURCE_DATE_EPOCH']);a.image=a.image.resolve();a.output=a.output.resolve();a.fwtool=a.fwtool.resolve()
assert a.image.stat().st_size==SIZE and sha(a.image)==a.sha256,'Source image checksum/size mismatch'
a.output.mkdir(parents=True,exist_ok=False);o=a.output
with a.image.open('rb') as f:prefix=f.read(4*M)
assert prefix[510:512]==b'\x55\xaa'
entries=[struct.unpack('<B3sB3sII',prefix[446+i*16:462+i*16]) for i in range(4)]
assert [(x[2],x[4],x[5]) for x in entries]==[(14,8192,131072),(131,139264,3956736),(0,0,0),(0,0,0)]
expected_id=0xc5bddd4c if a.storage=='sd' else 0xe95e0001
assert struct.unpack_from('<I',prefix,440)[0]==expected_id,'Storage identity mismatch'
(o/'prefix.bin').write_bytes(prefix)
extract(a.image,o/'boot.fat',4*M,64*M);extract(a.image,o/'root.ext4',68*M,1932*M)
dump(o/'root.ext4','/etc/openwrt_release',o/'openwrt_release')
release=dict(re.findall(r"^(DISTRIB_\w+)='([^']*)'$",(o/'openwrt_release').read_text(),re.M))
assert release['DISTRIB_ID']=='OpenWrt' and release['DISTRIB_TARGET']=='sunxi/cortexa53'
assert re.fullmatch(r'\d+\.\d+\.\d+',release['DISTRIB_RELEASE']), 'Stable release expected'
dump(o/'root.ext4','/usr/share/t95h/kernel-providers.json',o/'kernel-providers.json')
kernel=json.loads((o/'kernel-providers.json').read_text())['release']
platform=Path(__file__).resolve().parents[1]/'boards/t95h/openwrt/upgrade/platform.sh'
if a.platform is not None:platform=a.platform.resolve()
shutil.copyfile(platform,o/'platform.sh')
keep='/root/.ssh/\n/etc/config/\n/etc/dropbear/\n/etc/passwd\n/etc/shadow\n/etc/group\n/etc/uhttpd.key\n/etc/uhttpd.crt\n/etc/ttyd.key\n/etc/ttyd.crt\n/etc/sysupgrade.conf\n'
(o/'t95h-keep').write_text(keep)
changes=[('/lib/upgrade/platform.sh',o/'platform.sh',0o100644),('/lib/upgrade/keep.d/t95h',o/'t95h-keep',0o100644)]
commands=[]
for dst,src,mode in changes:
 # Replace both files; rm of a missing keep file is harmless in debugfs.
 commands.append(f'rm {dst}')
 commands.extend([f'write "{src}" {dst}',f'set_inode_field {dst} mode 0{mode:o}',f'set_inode_field {dst} uid 0',f'set_inode_field {dst} gid 0'])
 for field in ['atime','mtime','ctime','crtime']:commands.extend([f'set_inode_field {dst} {field} @{E}',f'set_inode_field {dst} {field}_extra 0'])
for dst in ['/lib/upgrade','/lib/upgrade/keep.d']:
 for field in ['atime','mtime','ctime']:commands.extend([f'set_inode_field {dst} {field} @{E}',f'set_inode_field {dst} {field}_extra 0'])
(o/'debugfs.commands').write_text('\n'.join(commands)+'\n')
(o/'debugfs.log').write_bytes(run('debugfs','-w','-f',o/'debugfs.commands',o/'root.ext4'))
flush(o/'root.ext4')
(o/'e2fsck.txt').write_bytes(run('e2fsck','-fn',o/'root.ext4'))
for dst,src,_ in changes:
 out=o/(src.name+'.verified');dump(o/'root.ext4',dst,out);assert sha(out)==sha(src)
# Keep the source kernel/DTB/FAT and entire boot prefix byte-identical.
name=f"t95h-openwrt-{release['DISTRIB_RELEASE']}-{kernel}"
if a.profile:name+='-'+a.profile
name+='-'+a.storage
install=o/(name+'-install.img')
install_expected=hashlib.sha256()
fd=os.open(install,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_DIRECT,0o644)
buf=mmap.mmap(-1,M)
try:
 for src in [o/'prefix.bin',o/'boot.fat',o/'root.ext4']:
  for data in direct_chunks(src):
   assert len(data)==M
   buf[:]=data
   if os.write(fd,buf)!=M:raise RuntimeError('Short direct install-image write')
   install_expected.update(data)
 os.fsync(fd)
finally:buf.close();os.close(fd)
flush(install)
assert install.stat().st_size==SIZE and sha(install)==install_expected.hexdigest()
print('Install image created; compressing matching partitions',flush=True)
gz(o/'boot.fat',o/'boot.gz');gz(o/'root.ext4',o/'root.gz')
manifest='\n'.join(['T95H-'+a.storage.upper()+'-UPGRADE-1',sha(o/'prefix.bin'),sha(o/'boot.gz'),sha(o/'root.gz'),sha(o/'boot.fat'),sha(o/'root.ext4'),'67108864 2025848832'])+'\n'
(o/'manifest').write_text(manifest)
upgrade=o/(name+'-sysupgrade.bin')
with tarfile.open(upgrade,'w',format=tarfile.USTAR_FORMAT) as tar:
 for n in ['manifest','boot.gz','root.gz']:
  info=tarfile.TarInfo(n);info.size=(o/n).stat().st_size;info.mode=0o644;info.mtime=E;info.uid=info.gid=0
  with (o/n).open('rb') as f:tar.addfile(info,f)
meta={'metadata_version':'1.1','compat_version':'1.0','supported_devices':['t95h,h616-tvbox'],'version':{'dist':'OpenWrt','version':release['DISTRIB_RELEASE'],'revision':release['DISTRIB_REVISION'],'target':release['DISTRIB_TARGET'],'board':'t95h'}}
(o/'metadata.json').write_text(json.dumps(meta,sort_keys=True,separators=(',',':'))+'\n')
run(a.fwtool,'-I',o/'metadata.json',upgrade)
flush(upgrade)
run(a.fwtool,'-i',o/'metadata.extracted.json',upgrade)
assert json.loads((o/'metadata.extracted.json').read_text())==meta
with tarfile.open(upgrade) as t:
 assert t.getnames()==['manifest','boot.gz','root.gz']
 for name,raw in [('boot.gz','boot.fat'),('root.gz','root.ext4')]:
  with gzip.GzipFile(fileobj=t.extractfile(name)) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==sha(o/raw)
proof={'source_image_sha256':a.sha256,'source_date_epoch':E,'openwrt':release,'custom_kernel':kernel,'kernel_rebuilt_in_packaging_step':False,'profile':a.profile,'storage':a.storage,'boot_and_dtb_unchanged':True,'boot_prefix_sha256':sha(o/'prefix.bin'),'boot_sha256':sha(o/'boot.fat'),'rootfs_sha256':sha(o/'root.ext4'),'platform_sha256':sha(o/'platform.sh'),'keep_sha256':sha(o/'t95h-keep'),'install_image':install.name,'install_sha256':sha(install),'sysupgrade':upgrade.name,'sysupgrade_sha256':sha(upgrade),'sysupgrade_bytes':upgrade.stat().st_size,'hardware_upgrade_tested':False,'signed':False,'tools':{'python':os.sys.version.split()[0],'debugfs':subprocess.run(['debugfs','-V'],capture_output=True,text=True).stderr.splitlines()[0],'fwtool_sha256':sha(a.fwtool)}}
(o/'build-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
(o/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in [install,upgrade,o/'platform.sh']))
print(json.dumps(proof,indent=2),flush=True)
