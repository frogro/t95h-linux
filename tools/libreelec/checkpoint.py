#!/usr/bin/env python3
"""Preserve a quiescent LibreELEC tree, including symlinks, modes and build stamps."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MEMBERS=['build/libreelec','build/libreelec-inputs','build/libreelec-request.json']
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def cpu_flags():
 for line in Path('/proc/cpuinfo').read_text().splitlines():
  if line.startswith('flags'):
   return set(line.split(':',1)[1].split())
 return set()
def identity():
 return {'format':1,'workspace':str(ROOT),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'runner_image':os.environ.get('ImageOS',''),'request':json.loads((ROOT/'build/libreelec-request.json').read_text())}
def packaging_only_migration(old, new):
 # One explicitly reviewed checkpoint. Kernel, toolchain, source resolution,
 # firmware bytes and all compiled-package inputs must remain unchanged.
 if old != 'eddc4db5d27c90788c064c7a028ef76b8f1fcf16':return False
 allowed={
  'boards/t95h/openwrt/runtime-lock.json',
  'boards/t95h/openwrt/runtime/B/usr/sbin/t95h-gpu-start',
  'docs/anotter-kiosk.md','docs/openwrt-gpu-start-45s.md',
  'tools/anotter/build.py','tools/build-openwrt-release.py',
  'boards/t95h/libreelec/hardware/package.mk',
  '.github/workflows/libreelec-phase.yml','tools/libreelec/checkpoint.py',
  'tools/libreelec/refresh-firmware-package.py',
  'tests/test_libreelec_firmware.py',
  'tools/libreelec/assemble.py','tests/test_libreelec_assemble.py',
 }
 changed=set(subprocess.check_output(['git','diff','--name-only',old,new],cwd=ROOT,text=True).splitlines())
 return bool(changed) and changed <= allowed
def save(out):
 out.mkdir(parents=True,exist_ok=True)
 archive=out/'state.tar.zst'
 subprocess.run(['tar','--use-compress-program=zstd -T2 -3','-cf',str(archive),*MEMBERS],cwd=ROOT,check=True)
 m=identity();m['cpu_flags']=sorted(cpu_flags());m['sha256']=digest(archive);(out/'state.json').write_text(json.dumps(m,indent=2)+'\n')
 print('Checkpoint saved and hashed',flush=True)
def restore(source):
 m=json.loads((source/'state.json').read_text());current=identity()
 for k in ('format','workspace','commit','runner_image','request'):
  if m[k]!=current[k]:
   if k=='commit' and packaging_only_migration(m[k],current[k]):
    print('Applying reviewed firmware-packaging checkpoint migration',flush=True)
   else:raise ValueError('Checkpoint identity differs: '+k)
 if not set(m.get('cpu_flags',[])).issubset(cpu_flags()):raise ValueError('Checkpoint host compiler requires CPU features absent on this runner')
 archive=source/'state.tar.zst'
 if digest(archive)!=m['sha256']:raise ValueError('Checkpoint checksum mismatch')
 if (ROOT/'build/libreelec').exists():raise ValueError('Refusing to overwrite an existing build tree')
 # Archive originates only from a same-commit Actions run; preserve its toolchain symlinks.
 subprocess.run(['tar','--no-same-owner','--use-compress-program=zstd','-xf',str(archive)],cwd=ROOT,check=True)
 if identity()!=current:raise ValueError('Restored request changed')
 print('Checkpoint restored: source, toolchain, packages and stamps',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['save','restore']);p.add_argument('directory',type=Path);a=p.parse_args();globals()[a.mode](a.directory.resolve())
