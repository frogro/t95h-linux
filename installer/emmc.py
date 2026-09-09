#!/usr/bin/env python3
"""Read-only eMMC preflight. This does not install or erase anything."""
import argparse
import datetime
import getpass
import json
from pathlib import Path
import re

PROBE = r'''
set -e
printf 'board='; tr '\000' '|' < /proc/device-tree/compatible; echo
rootmm=$(awk '$5=="/" && $0 ~ / - ext4 / {print $3; exit}' /proc/self/mountinfo)
[ -n "$rootmm" ]
printf 'root='; basename "$(readlink -f /sys/dev/block/$rootmm)"
for d in /sys/class/block/mmcblk[0-9]*; do
 name=${d##*/}
 case "$name" in *p*|*boot*|*rpmb*) continue;; esac
 [ -r "$d/device/type" ] || continue
 printf 'disk=%s,' "$name"
 tr -d '\n' < "$d/device/type"; printf ','
 tr -d '\n' < "$d/device/cid"; printf ','
 tr -d '\n' < "$d/size"; echo
done
'''

def identify(text):
    fields = text.splitlines()
    board = next((x[6:] for x in fields if x.startswith('board=')), '')
    if 't95h,h616-tvbox' not in board.split('|'): raise ValueError('Unexpected board')
    root = next((x[5:] for x in fields if x.startswith('root=')), '')
    match = re.fullmatch(r'(mmcblk[0-9]+)p[0-9]+',root)
    if not match: raise ValueError('Root is not a direct MMC partition')
    disks=[]
    for line in fields:
        if not line.startswith('disk='): continue
        name,kind,cid,sectors = line[5:].split(',')
        if not re.fullmatch(r'mmcblk[0-9]+',name) or not re.fullmatch(r'[0-9a-fA-F]{32}',cid):
            raise ValueError('Invalid device identity')
        disks.append(dict(device='/dev/'+name,name=name,type=kind,cid=cid,bytes=int(sectors)*512))
    roots=[d for d in disks if d['name']==match[1]]
    if len(roots)!=1 or roots[0]['type']!='SD': raise ValueError('Installer must run from SD')
    targets=[d for d in disks if d['type']=='MMC' and d['name']!=match[1]]
    if len(targets)!=1: raise ValueError('Exactly one internal eMMC must be visible')
    if targets[0]['bytes'] < 2097152000: raise ValueError('eMMC too small')
    return {'sd_root':root,'target':targets[0],'device_writes':False,'install_ready':False,
            'pending':['release-integrated eMMC image and installer',
                       'eMMC sysupgrade implementation and hardware validation'],
            'experimental_standalone_boot_observed':True}

def main():
    import paramiko
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host',default='192.168.178.177')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    c=paramiko.SSHClient();c.load_system_host_keys();c.set_missing_host_key_policy(paramiko.RejectPolicy())
    c.connect(a.host,username='root',password=getpass.getpass('OpenWrt Root-Passwort: '),
              look_for_keys=False,allow_agent=False,timeout=10)
    a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    try:
        def read(cmd):
            i,o,e=c.exec_command(cmd,timeout=30);data=o.read();err=e.read();rc=o.channel.recv_exit_status()
            i.close();o.close();e.close()
            if rc:raise RuntimeError(err.decode(errors='replace'))
            return data
        raw=read(PROBE);(a.output/'identity.txt').write_bytes(raw)
        report=identify(raw.decode())
        # Capture mount and holder state; no write operation is offered by this tool.
        (a.output/'mountinfo.txt').write_bytes(read('cat /proc/self/mountinfo'))
        (a.output/'swaps.txt').write_bytes(read('cat /proc/swaps'))
        report['captured_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (a.output/'preflight.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:c.close()

if __name__=='__main__':main()
