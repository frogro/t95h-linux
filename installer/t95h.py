#!/usr/bin/env python3
"""ThinkPad entry point: prepare an OpenWrt profile locally or through Actions."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('command',choices=['prepare','dispatch','status','download'])
p.add_argument('--profile',choices=['base','base-A','base-B','base-A-B'],default='base-A-B')
p.add_argument('--console',choices=['dual','hdmi','uart'],default='dual')
p.add_argument('--repo',default='frogro/t95h-linux')
p.add_argument('--output',type=Path,default=ROOT/'build/request.json')
p.add_argument('--run-id',type=int)
a=p.parse_args()
if a.command=='prepare':
 subprocess.run([sys.executable,str(ROOT/'tools/check-repository.py')],check=True)
 subprocess.run([sys.executable,str(ROOT/'tools/resolve-stable-versions.py'),'--profile',a.profile,'--console',a.console,'--output',str(a.output)],check=True)
elif a.command=='dispatch':
 subprocess.run(['gh','workflow','run','prepare-openwrt.yml','--repo',a.repo,'-f','profile='+a.profile,'-f','console='+a.console],check=True)
 print('Vorbereitung gestartet. Dieser Workflow erzeugt noch kein Image. Status mit: t95h.py status')
elif a.command=='status':
 subprocess.run(['gh','run','list','--repo',a.repo,'--workflow','prepare-openwrt.yml','--limit','5'],check=True)
else:
 if not a.run_id:p.error('--run-id is required for download')
 destination=ROOT/'build'/'actions'/str(a.run_id)
 subprocess.run(['gh','run','download',str(a.run_id),'--repo',a.repo,'--name','t95h-build-preparation','--dir',str(destination)],check=True)
 print('Vorbereitungsberichte:',destination)
