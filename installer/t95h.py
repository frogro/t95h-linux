#!/usr/bin/env python3
"""ThinkPad entry point: prepare an OpenWrt profile locally or through Actions."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(command, **kwargs):
    try:
        return subprocess.run(command, **kwargs)
    except subprocess.CalledProcessError as error:
        raise SystemExit('STOP: Befehl fehlgeschlagen (Exit '+str(error.returncode)+'). Kein Erfolg bestätigt; vor erneutem Dispatch zuerst Status prüfen.')

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('command',choices=['prepare','dispatch','status','download','access'])
p.add_argument('--profile',choices=['base','base-A','base-B','base-A-B'],default='base-A-B')
p.add_argument('--console',choices=['dual','hdmi','uart'],default='dual')
p.add_argument('--repo',default='frogro/t95h-linux')
p.add_argument('--output',type=Path,default=ROOT/'build/request.json')
p.add_argument('--run-id',type=int)
a=p.parse_args()
if a.command=='access':
 from access import prepare
 try:
  prepare(ROOT)
 except (ValueError, OSError) as error:
  raise SystemExit('STOP: '+str(error))
elif a.command=='prepare':
 run([sys.executable,str(ROOT/'tools/check-repository.py')],check=True)
 run([sys.executable,str(ROOT/'tools/resolve-stable-versions.py'),'--profile',a.profile,'--console',a.console,'--output',str(a.output)],check=True)
elif a.command=='dispatch':
 run(['gh','workflow','run','build-openwrt.yml','--repo',a.repo,'--ref','main','-f','profile='+a.profile,'-f','console='+a.console],check=True)
 print('Vollständiger Build gestartet: Installationsimage und Sysupgrade. Status mit: python3 installer/t95h.py status')
elif a.command=='status':
 run(['gh','run','list','--repo',a.repo,'--workflow','build-openwrt.yml','--limit','5'],check=True)
else:
 if not a.run_id:p.error('--run-id is required for download')
 info=json.loads(run(['gh','run','view',str(a.run_id),'--repo',a.repo,'--json','status,conclusion'],check=True,capture_output=True,text=True).stdout)
 if info.get('status')!='completed' or info.get('conclusion')!='success':raise SystemExit('STOP: Build noch nicht erfolgreich abgeschlossen.')
 destination=ROOT/'build'/'actions'/str(a.run_id)
 run(['gh','run','download',str(a.run_id),'--repo',a.repo,'--name','t95h-'+a.profile+'-'+a.console+'-install-sysupgrade','--dir',str(destination)],check=True)
 from verify_release import verify
 try:
  checked=verify(destination)
 except (ValueError,OSError) as error:
  raise SystemExit('STOP: '+str(error))
 print('PASS: Prüfsummen geprüft:',', '.join(checked))
 print('Installationsimage, Sysupgrade und Prüfberichte:',destination)
