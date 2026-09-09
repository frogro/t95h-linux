#!/usr/bin/env python3
import argparse,hashlib,json,mmap,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--a',type=Path,required=True);p.add_argument('--b',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
x=json.loads((a.a/'build-proof.json').read_text());y=json.loads((a.b/'build-proof.json').read_text())
for k in ['install_sha256','sysupgrade_sha256','rootfs_sha256','boot_sha256','platform_sha256','source_image_sha256']:assert x[k]==y[k],k
r={'passed':False,'install_sha256':x['install_sha256'],'sysupgrade_sha256':x['sysupgrade_sha256'],'direct_reads':{}}
for folder in [a.a,a.b]:
 for name,key in [(x['install_image'],'install_sha256'),(x['sysupgrade'],'sysupgrade_sha256')]:
  f=folder/name;digests=[]
  for attempt in range(2):
   fd=os.open(f,os.O_RDONLY|os.O_DIRECT);buf=mmap.mmap(-1,1048576);h=hashlib.sha256()
   try:
    for off in range(0,f.stat().st_size,1048576):
     n=os.preadv(fd,[buf],off);assert n==min(1048576,f.stat().st_size-off);h.update(buf[:n])
   finally:buf.close();os.close(fd)
   digests.append(h.hexdigest());assert digests[-1]==x[key],(f,digests)
  r['direct_reads'][folder.name+'/'+name]=digests;print(folder.name,name,'PASS',flush=True)
r['passed']=True;a.output.write_text(json.dumps(r,indent=2)+'\n')
