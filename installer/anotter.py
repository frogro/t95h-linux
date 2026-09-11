#!/usr/bin/env python3
"""Dispatch/download AnotterKiosk, or configure SSH on an already flashed SD."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

def access(boot, key):
    boot=boot.resolve(strict=True); key=key.resolve(strict=True)
    if not (boot/'kioskbrowser.ini').is_file() or not (boot/'boot/t95h.dtb').is_file():
        raise ValueError('Keine T95H-Anotter-Bootpartition')
    text=key.read_text().strip()
    if '\n' in text or not re.match(r'^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp\d+) [A-Za-z0-9+/=]+(?: .*)?$',text):
        raise ValueError('Eine öffentliche SSH-Schlüsseldatei (.pub) angeben')
    subprocess.run(['ssh-keygen','-l','-f',str(key)],check=True)
    target=boot/'authorized_keys'
    existing=target.read_text() if target.exists() else ''
    if text not in existing.splitlines(): target.write_text(existing.rstrip()+'\n'+text+'\n' if existing else text+'\n')
    if text not in target.read_text().splitlines(): raise ValueError('Schlüsselübernahme fehlgeschlagen')
    print('SSH-Schlüssel übernommen. Anmeldung: ssh root@<DHCP-IP-der-Box>')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['dispatch','status','download','access'])
    p.add_argument('--tag'); p.add_argument('--output',type=Path,default=Path('build/anotter-download'))
    p.add_argument('--boot',type=Path); p.add_argument('--key',type=Path,default=Path.home()/'.ssh/id_ed25519.pub')
    a=p.parse_args(); base=['gh']; repo=['--repo','frogro/t95h-linux']
    if a.command=='access':
        if not a.boot: p.error('--boot <eingehängte Bootpartition> fehlt')
        access(a.boot,a.key)
    elif a.command=='dispatch':
        subprocess.run(base+['workflow','run','build-anotter.yml','--ref','main']+repo,check=True)
    elif a.command=='status':
        subprocess.run(base+['run','list','--workflow','build-anotter.yml','--limit','5']+repo,check=True)
    else:
        if not a.tag or not re.fullmatch(r'anotter-\d+-\d+',a.tag): p.error('--tag anotter-RUN-ATTEMPT fehlt')
        subprocess.run(base+['release','download',a.tag,'--dir',str(a.output)]+repo,check=True)
        manifest=json.loads((a.output/'manifest.json').read_text()); name=manifest['image']
        if Path(name).name!=name: raise ValueError('Ungültiger Image-Dateiname')
        with (a.output/name).open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        if digest!=manifest['sha256']: raise ValueError('Image-Prüfsumme stimmt nicht')
        print('Image geprüft:',a.output/name)
        print('Entpacken und mit einer Image-Schreibanwendung auf SD schreiben; danach access aufrufen. Kein Datenträger wurde beschrieben.')
if __name__=='__main__': main()
