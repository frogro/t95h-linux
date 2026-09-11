#!/usr/bin/env python3
"""Compile one profile from a verified source replay and locked firmware files."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
# Kconfig def_bool probes of host tools, not requested target drivers/features.
HOST_PROBES={
 'CONFIG_OPENSSL_SUPPORTS_ML_DSA','CONFIG_PAHOLE_HAS_LANG_EXCLUDE',
 # init/Kconfig def_bool RUSTC_VERSION comparisons, not target features.
 'CONFIG_RUSTC_HAS_SPAN_FILE','CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES',
 'CONFIG_RUSTC_HAS_FILE_WITH_NUL','CONFIG_RUSTC_HAS_FILE_AS_C_STR',
}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source-stage',type=Path,required=True)
 p.add_argument('--toolchain',type=Path,required=True)
 p.add_argument('--firmware-root',type=Path,required=True,help='Directory containing lib/firmware files')
 p.add_argument('--profile',choices=['base','base-A','base-B','base-A-B'],default='base-A-B')
 p.add_argument('--config',type=Path,help='Explicit OS-specific config; profile still selects firmware')
 p.add_argument('--output',type=Path,required=True);p.add_argument('--jobs',type=int,default=3)
 p.add_argument('--epoch',type=int,required=True)
 a=p.parse_args()
 if not 1<=a.jobs<=64:raise ValueError('Invalid job count')
 stage=a.source_stage.resolve(strict=True);proof=json.loads((stage/'source-report.json').read_text())
 if not proof['source_preparation_passed']:raise ValueError('Source replay not verified')
 source=stage/('linux-'+proof['kernel']);board=ROOT/'boards/t95h'
 lock=json.loads((board/'kernel/source-lock.json').read_text())
 for entry in lock['files']:
  expected=proof['incremental_files'].get(entry['path'],entry['sha256'])
  if sha(source/entry['path'])!=expected:raise ValueError('Source changed: '+entry['path'])
 tc=a.toolchain.resolve(strict=True);prefix=tc/'bin/aarch64-openwrt-linux-musl-'
 compiler=Path(str(prefix)+'gcc');version=subprocess.check_output([str(compiler),'--version'],text=True).splitlines()[0]
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);(out/'tmp').mkdir()
 config=a.config.resolve(strict=True) if a.config else board/'profiles/kconfig-draft'/(a.profile+'.config');cfg=config.read_text();shutil.copyfile(config,out/'.config')
 groups={'base'}|set(a.profile.split('-')[1:])
 firmware={item['file']:item for item in json.loads((board/'profiles/integration-draft.json').read_text())['firmware'] if item['profile'] in groups}
 names=re.search(r'^CONFIG_EXTRA_FIRMWARE="(.*)"$',cfg,re.M).group(1).split()
 fwdir=source/'firmware';fwdir.mkdir(exist_ok=False);selected={}
 for name in names:
  rel='lib/firmware/'+name;entry=firmware[rel];src=a.firmware_root.resolve(strict=True)/rel
  if sha(src)!=entry['sha256']:raise ValueError('Firmware hash mismatch: '+rel)
  dst=fwdir/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  if sha(dst)!=entry['sha256']:raise ValueError('Firmware copy mismatch: '+rel)
  selected[rel]=entry['sha256']
 env=dict(os.environ,PATH=str(tc/'bin')+':'+os.environ['PATH'],STAGING_DIR=str(tc),TMPDIR=str(out/'tmp'),
          LC_ALL='C',TZ='UTC',SOURCE_DATE_EPOCH=str(a.epoch),
          KBUILD_BUILD_TIMESTAMP=datetime.datetime.fromtimestamp(a.epoch,datetime.timezone.utc).strftime('%a %b %d %H:%M:%S UTC %Y'),
          KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='t95h',KBUILD_BUILD_VERSION='1')
 cmd=['make','ARCH=arm64','CROSS_COMPILE='+str(prefix),'O='+str(out)]
 def status(state,**kwargs):
  (out/'build-status.json').write_text(json.dumps({'stage':state,'profile':a.profile,'comparison_build':False,'updated':time.time(),**kwargs},indent=2)+'\n')
 try:
  status('configuring')
  with (out/'build.log').open('w') as log:
   subprocess.run(cmd+['olddefconfig'],cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   actual=(out/'.config').read_text();requested={l for l in cfg.splitlines() if re.fullmatch(r'CONFIG_[A-Za-z0-9_]+=[ym]',l)}
   host_probe_changes=sorted(l for l in requested-set(actual.splitlines()) if l.split('=')[0] in HOST_PROBES)
   missing=sorted(l for l in requested-set(actual.splitlines()) if l.split('=')[0] not in HOST_PROBES)
   (out/'host-probe-differences.json').write_text(json.dumps(host_probe_changes,indent=2)+'\n')
   if missing:raise ValueError('Selected kernel functions changed during configuration: '+repr(missing))
   status('compiling',compiler=version,compiler_sha256=sha(compiler),firmware=selected,config_sha256=sha(out/'.config'))
   print('Compiling one',a.profile,'kernel; log:',out/'build.log',flush=True)
   subprocess.run(cmd+['-j'+str(a.jobs),'Image','modules'],cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  status('kernel-complete',image_sha256=sha(out/'arch/arm64/boot/Image'),config_sha256=sha(out/'.config'),
         firmware=selected,compiler=version,compiler_sha256=sha(compiler),image_ready=False,
         remaining=['External modules and kernel APK','Bootchain and final image pair'])
  print('PASS: kernel and in-tree modules compiled. No bootable image yet.')
 except Exception as error:
  status('failed',error=str(error));raise
if __name__=='__main__':main()
