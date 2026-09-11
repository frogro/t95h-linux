#!/usr/bin/env python3
"""Assemble a fresh FAT/ext4 SD image with an explicitly locked tested boot prefix."""
import argparse,hashlib,importlib.util,json,os,shutil,subprocess
from pathlib import Path
from direct_image_io import concatenate
ROOT=Path(__file__).resolve().parents[1];M=1048576

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inventory(root):
 out={}
 for p in sorted(root.rglob('*')):
  rel=str(p.relative_to(root))
  if p.is_symlink():out[rel]={'link':os.readlink(p)}
  elif p.is_file():out[rel]={'sha256':sha(p),'mode':p.stat().st_mode&0o7777}
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['rootfs-stage','prefix','imagebuilder','output']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--console',choices=['dual','hdmi','uart'],default='dual');p.add_argument('--epoch',type=int,required=True)
 a=p.parse_args();stage=a.rootfs_stage.resolve(strict=True);proof=json.loads((stage/'rootfs-report.json').read_text())
 if not proof['rootfs_preparation_passed'] or not proof.get('kernel_payload_validated'):raise ValueError('Verified fresh rootfs required')
 lock=json.loads((ROOT/'boards/t95h/boot/tested-prefix-lock.json').read_text());prefix=a.prefix.resolve(strict=True)
 if prefix.stat().st_size!=lock['bytes'] or sha(prefix)!=lock['sha256']:raise ValueError('Boot prefix differs from tested lock')
 host=a.imagebuilder.resolve(strict=True)/'staging_dir/host/bin'
 for name in ['mkfs.fat','mcopy','fsck.fat']:
  if not (host/name).is_file():raise ValueError('Missing host tool: '+name)
 output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
 root=output/'root';shutil.copytree(stage/'root',root,symlinks=True)
 # Boot payload belongs to FAT. Keep only an empty rootfs mountpoint.
 if (root/'boot').exists():shutil.rmtree(root/'boot')
 (root/'boot').mkdir()
 boot=output/'fat-files/boot';boot.mkdir(parents=True)
 for name in ['Image','t95h.dtb']:shutil.copyfile(stage/'kernel-boot'/name,boot/name)
 # Paired per-profile DTBs permit disabling USB0 host without changing other hardware.
 shutil.copyfile(boot/'t95h.dtb',boot/'t95h-usb0-host.dtb')
 shutil.copyfile(boot/'t95h.dtb',boot/'t95h-usb0-off.dtb')
 for node in ['/soc/usb@5101000','/soc/usb@5101400']:
  subprocess.run(['fdtput','-t','s',str(boot/'t95h-usb0-off.dtb'),node,'status','disabled'],check=True)
  subprocess.run(['fdtput','-d',str(boot/'t95h-usb0-off.dtb'),node,'dr_mode'],check=True)
 (boot/'usb0-modes.sha256').write_text(''.join(sha(boot/n)+'  '+n+'\n' for n in ['t95h-usb0-host.dtb','t95h-usb0-off.dtb']))
 scripts=ROOT/'boards/t95h/boot/scripts';hashes=json.loads((scripts/'sha256.json').read_text())
 for name,h in hashes.items():
  if sha(scripts/name)!=h:raise ValueError('Boot script changed: '+name)
 spec=importlib.util.spec_from_file_location('console',ROOT/'tools/configure-boot-console.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 shutil.copyfile(scripts/'boot.scr',boot/'boot.scr')
 (boot/'boot.scm').write_bytes(mod.configure((scripts/'boot.scm').read_bytes(),a.console))
 # Check module paths used by the late services, not only depmod's inventory.
 metadata=json.loads((root/'usr/share/t95h/build-profile.json').read_text());release=metadata['kernel']
 if not (root/'lib/modules'/release/'t95h_aldo2.ko').is_file():raise ValueError('Late WLAN regulator path missing')
 if 'B' in proof['profile'].split('-'):
  # Profile B must ship the guarded late Panfrost service enabled.
  autostart=root/'etc/rc.d/S99t95h-gpu'
  if not autostart.is_symlink() or os.readlink(autostart)!='../init.d/t95h-gpu':
   raise ValueError('Profile B Panfrost autostart missing or incorrect')
  gpu=root/'usr/lib/t95h-gpu'
  if (gpu/'SHA256SUMS').read_text()!=sha(gpu/'t95h_ana_provider.ko')+'  t95h_ana_provider.ko\n':raise ValueError('Late GPU module checksum mismatch')
 for folder in [root,boot.parent]:
  for f in folder.rglob('*'):os.utime(f,(a.epoch,a.epoch),follow_symlinks=False)
  os.utime(folder,(a.epoch,a.epoch))
 expected=inventory(root);fat=output/'boot.fat';fs=output/'root.ext4'
 for f,size in [(fat,64*M),(fs,1932*M)]:
  with f.open('xb') as stream:stream.truncate(size)
 env=dict(os.environ,LC_ALL='C',TZ='UTC',SOURCE_DATE_EPOCH=str(a.epoch),E2FSPROGS_FAKE_TIME=str(a.epoch))
 with (output/'assembly.log').open('w') as log:
  def run(cmd):subprocess.run(list(map(str,cmd)),env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  run([host/'mkfs.fat','--invariant','-F','16','-i','54393548','-n','T95HBOOT',fat])
  run([host/'mcopy','-m','-s','-i',fat,boot,'::/']);run([host/'fsck.fat','-n',fat])
  # fakeroot supplies root ownership to mkfs without changing host file ownership.
  run(['fakeroot','sh','-c','chown -hR 0:0 "$1" && exec mkfs.ext4 -q -F -b 4096 -N 524288 -U 95361601-0000-4000-8000-000000000002 -L T95HROOT -O ^has_journal -E lazy_itable_init=0 -d "$1" "$2"','t95h-image',root,fs])
  run(['e2fsck','-fn',fs])
  verify=output/'verify-root';verify.mkdir()
  run(['fakeroot','debugfs','-R','rdump / '+str(verify),fs])
  actual=inventory(verify)
  if actual!=expected:raise ValueError('Rootfs readback inventory mismatch; inspect verify-root')
  for name in ['Image','t95h.dtb','boot.scr','boot.scm','t95h-usb0-host.dtb','t95h-usb0-off.dtb','usb0-modes.sha256']:
   dest=output/('fat-readback-'+name);run([host/'mcopy','-i',fat,'::/boot/'+name,dest])
   if sha(dest)!=sha(boot/name):raise ValueError('FAT readback differs: '+name)
 image=output/'t95h-base.img'
 try:
  direct=concatenate([prefix,fat,fs],image)
 except Exception as error:
  (output/'image-failure.json').write_text(json.dumps({'stage':'direct-image-assembly','error':str(error)})+'\n')
  raise
 if image.stat().st_size!=2000*M:raise ValueError('Image size differs')
 report={'image':image.name,'sha256':direct['sha256'],'direct_readback_count':direct['direct_readback_count'],'bytes':image.stat().st_size,'profile':proof['profile'],'openwrt':proof['openwrt'],'console':a.console,'boot_prefix_sha256':direct['source_sha256'][str(prefix)],'rootfs_sha256':direct['source_sha256'][str(fs)],'fat_sha256':direct['source_sha256'][str(fat)],'rootfs_payload_readback_verified':True,'fat_payload_readback_verified':True,'hardware_tested':False,'sysupgrade_pair_ready':False}
 (output/'image-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
