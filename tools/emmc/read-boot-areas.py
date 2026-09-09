#!/usr/bin/env python3
"""Read eMMC boot0/boot1 over verified SSH, twice; never write to the device."""
import argparse
import getpass
import hashlib
import json
from pathlib import Path
import re
import paramiko


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--host',default='192.168.178.177')
 p.add_argument('--output',required=True,type=Path)
 a=p.parse_args()
 password=getpass.getpass('OpenWrt Root-Passwort: ')
 c=paramiko.SSHClient();c.load_system_host_keys();c.set_missing_host_key_policy(paramiko.RejectPolicy())
 c.connect(a.host,username='root',password=password,look_for_keys=False,allow_agent=False,timeout=10)
 def read(command):
  i,o,e=c.exec_command(command,timeout=60);data=o.read();error=e.read();rc=o.channel.recv_exit_status()
  if rc:raise RuntimeError((command,rc,error.decode(errors='replace')))
  return data
 try:
  listing=read('for d in /sys/class/block/mmcblk*boot[01]; do [ ! -e "$d" ] || echo "${d##*/}"; done').decode().splitlines()
  if not listing:raise RuntimeError('No eMMC boot areas exposed; nothing captured')
  if any(not re.fullmatch(r'mmcblk[0-9]+boot[01]',name) for name in listing):raise RuntimeError('Unexpected device name')
  records=[]
  # Finish all identification checks before reading any boot payload.
  for name in listing:
   base=name.split('boot')[0]
   if read('cat /sys/class/block/'+base+'/device/type').strip()!=b'MMC':raise RuntimeError('Not eMMC')
   size=int(read('cat /sys/class/block/'+name+'/size'))*512
   if not 0<size<=64*1024*1024:raise RuntimeError('Unexpected boot-area size')
   if read('cat /sys/class/block/'+name+'/ro').strip()!=b'1':raise RuntimeError('Boot area is not read-only')
   records.append({'name':name,'bytes':size,'parent':base})
  out=a.output.resolve();out.mkdir(parents=True,exist_ok=False,mode=0o700)
  report={'device_writes':False,'host':a.host,'boot_areas':[],'rpmb_payload_captured':False}
  for item in records:
   name=item['name'];data=read('cat /dev/'+name)
   if len(data)!=item['bytes']:raise RuntimeError('Short first read')
   file=out/(name+'.bin');file.write_bytes(data);file.chmod(0o600)
   second=read('cat /dev/'+name)
   if second!=data or file.read_bytes()!=data:raise RuntimeError('Repeated read or saved file differs')
   item.update(sha256=hashlib.sha256(data).hexdigest(),double_read_verified=True,
               cid=read('cat /sys/class/block/'+item['parent']+'/device/cid').decode().strip())
   report['boot_areas'].append(item)
   print(name,'PASS',item['bytes'],'bytes',item['sha256'])
  report['passed']=True
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');(out/'report.json').chmod(0o600)
  print('Read-only capture saved locally:',out)
 finally:c.close()
if __name__=='__main__':main()
