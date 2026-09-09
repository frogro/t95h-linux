#!/usr/bin/env python3
"""Run official postinstall and stage locked board services in a fresh root copy.

Development stage only. Does not create, flash or publish an image.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--packages',required=True,type=Path)
 p.add_argument('--imagebuilder',required=True,type=Path)
 p.add_argument('--compiler',required=True,type=Path)
 p.add_argument('--output',required=True,type=Path)
 p.add_argument('--epoch',required=True,type=int)
 a=p.parse_args();source=a.packages.resolve(strict=True)
 proof=json.loads((source/'package-lock.json').read_text())
 if not proof['package_stage_passed']:raise ValueError('Package stage failed')
 ib=a.imagebuilder.resolve(strict=True);compiler=a.compiler.resolve(strict=True)
 if 'openwrt-imagebuilder-'+proof['openwrt']+'-sunxi-cortexa53.' not in ib.name:raise ValueError('Wrong ImageBuilder')
 if sha(ib/'staging_dir/host/bin/apk')!=proof['host_apk_sha256']:raise ValueError('ImageBuilder APK changed')
 subprocess.run(['python3',str(ROOT/'tools/check-repository.py')],check=True,stdout=subprocess.DEVNULL)
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 root=out/'root';shutil.copytree(source/'root',root,symlinks=True)
 (out/'tmp').mkdir();shutil.copytree(root/'boot',out/'kernel-boot',symlinks=True)
 env=dict(os.environ,STAGING_DIR_HOST=str(ib/'staging_dir/host'),TMPDIR=str(out/'tmp'),
          TZ='UTC',LC_ALL='C',SOURCE_DATE_EPOCH=str(a.epoch),
          PATH=str(ib/'staging_dir/host/bin')+':'+os.environ['PATH'])
 def run(command,**kwargs):
  with (out/'prepare.log').open('a') as log:
   subprocess.run(list(map(str,command)),env=env,stdout=log,stderr=subprocess.STDOUT,check=True,**kwargs)
 print('Official OpenWrt postinstall; log:',out/'prepare.log',flush=True)
 run(['make','prepare_rootfs','TARGET_DIR='+str(root),'SOURCE_DATE_EPOCH='+str(a.epoch)],cwd=ib)
 # Target paths are only inside this fresh tree; never follow a host-pointing symlink.
 def destination(rel):
  path=root/rel
  for parent in [path,*path.parents]:
   if parent==root:break
   if parent.is_symlink():raise ValueError('Refusing overlay through symlink: '+str(parent))
  path.parent.mkdir(parents=True,exist_ok=True)
  return path
 board=ROOT/'boards/t95h';lock=json.loads((board/'openwrt/runtime-lock.json').read_text())
 groups={'base'}|set(proof['profile'].split('-')[1:]);runtime={}
 for name,entry in lock['files'].items():
  if entry['profile'] not in groups:continue
  rel=Path(name).relative_to('openwrt/runtime/'+entry['profile'])
  src=board/name;dst=destination(rel);shutil.copyfile(src,dst)
  mode=0o600 if str(rel).startswith('etc/config/') else int(entry['mode'],8)
  dst.chmod(mode);runtime[str(rel)]=sha(dst)
 # Standard credentials are public defaults; never copy a device's shadow or keys.
 shadow=destination('etc/shadow')
 hashed=subprocess.run(['openssl','passwd','-6','-salt','t95hdefault','-stdin'],input='openwrt\n',text=True,capture_output=True,check=True).stdout.strip()
 lines=shadow.read_text().splitlines()
 if sum(line.startswith('root:') for line in lines)!=1:raise ValueError('Unexpected shadow root entry')
 shadow.write_text('\n'.join('root:'+hashed+':0:0:99999:7:::' if line.startswith('root:') else line for line in lines)+'\n');shadow.chmod(0o600)
 # Board detection belongs to the fixed T95H recipe, not generic sunxi defaults.
 shutil.rmtree(root/'etc/board.d')
 destination('etc/board.json').write_text(json.dumps({'model':{'id':'t95h,h616-tvbox','name':'T95H H616'},'network':{'lan':{'device':'eth0','protocol':'dhcp'}}},indent=2)+'\n')
 for rel in ('etc/urandom.seed','etc/machine-id','etc/fw_env.config'):
  path=root/rel
  if path.exists() or path.is_symlink():path.unlink()
 for name in ('t95h-fd655','t95h-upgrade-report'):
  src=board/'external/display/t95h-fd655.c' if name=='t95h-fd655' else ROOT/'tools/upgrade-progress/report.c'
  dst=destination('usr/'+('sbin/' if name=='t95h-fd655' else 'libexec/')+name)
  run([compiler,'-Os',src,'-o',dst]);dst.chmod(0o755)
 shutil.copyfile(board/'openwrt/upgrade/platform.sh',destination('lib/upgrade/platform.sh'))
 for path in (root/'etc/init.d').glob('t95h-*'):
  for link in (root/'etc/rc.d').glob('*'+path.name):link.unlink()
  if path.name in lock.get('inactive_legacy_services',[]):continue
  match=re.search(r'^START=(\d+)$',path.read_text(),re.M)
  if not match:raise ValueError('Service missing START: '+path.name)
  (root/'etc/rc.d'/('S'+match[1].zfill(2)+path.name)).symlink_to('../init.d/'+path.name)
 for path in (root/'etc/rc.d').glob('*ustreamer'):path.unlink()
 forbidden=list(root.glob('etc/dropbear/dropbear_*_host_key'))+list(root.glob('root/.ssh/*'))
 if forbidden:raise ValueError('Unexpected device keys in fresh root')
 report={'rootfs_preparation_passed':True,'bootable_image_ready':False,'previous_image_used':False,
         'profile':proof['profile'],'openwrt':proof['openwrt'],'runtime':runtime,
         'default_root_password':'documented public default initialized',
         'kernel_source_release_validated':False,
         'compiler_sha256':sha(compiler),
         'remaining':['Profile DT and firmware verification','Kernel rebuild with selected source patch',
                      'USB autoload and ModemManager guard','GPU startup without AP','Bootchain and image pair']}
 (out/'rootfs-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS: postinstall, board services and default access prepared; image not ready.')
if __name__=='__main__':main()
