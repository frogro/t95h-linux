#!/usr/bin/env python3
"""Derive the hardware-tested eMMC prefix from locked SD input. No device I/O."""
import hashlib,json,struct
from pathlib import Path
import libfdt
ROOT=Path(__file__).resolve().parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def prepare(source,output):
 lock=json.loads((ROOT/'boards/t95h/boot/emmc/lock.json').read_text())
 old=source.read_bytes()
 if len(old)!=4194304 or sha(old)!=lock['source_prefix_sha256']:raise ValueError('Unexpected source boot prefix')
 spl=(ROOT/'boards/t95h/boot/emmc/spl-reset-fifo.toc0').read_bytes()
 if len(spl)!=40960 or sha(spl)!=lock['spl_sha256']:raise ValueError('SPL lock mismatch')
 b=bytearray(old);b[8192:49152]=spl
 size=struct.unpack_from('>I',b,49156)[0];fit=libfdt.Fdt(bytes(b[49152:49152+size]))
 node=fit.path_offset('/images/fdt-1');dt=libfdt.Fdt(bytes(fit.getprop(node,'data')))
 dt.setprop(dt.path_offset('/aliases'),'mmc0',b'/soc/mmc@4022000\0')
 off=dt.path_offset('/soc/mmc@4022000');dt.setprop(off,'max-frequency',struct.pack('>I',25000000))
 for key in ('cap-sd-highspeed','cap-mmc-highspeed','mmc-ddr-3_3v','mmc-ddr-1_8v','mmc-hs200-1_8v','cap-sdio-irq'):
  try:dt.delprop(off,key)
  except libfdt.FdtException as e:
   if e.err != -libfdt.NOTFOUND:raise
 fit.setprop(node,'data',bytes(dt.as_bytearray()))
 if len(fit.as_bytearray())!=size:raise ValueError('FIT size changed')
 b[49152:49152+size]=bytes(fit.as_bytearray());struct.pack_into('<I',b,440,0xe95e0001)
 if sha(b)!=lock['prefix_sha256']:raise ValueError('Derived prefix differs from tested recipe')
 with output.open('xb') as f:f.write(b)
 return lock
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.source,a.output),indent=2))
