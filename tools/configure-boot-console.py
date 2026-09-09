#!/usr/bin/env python3
"""Set console mode in a validated legacy U-Boot script; retain other bootargs."""
import struct,zlib,re,argparse
from pathlib import Path

def configure(blob,mode):
 h=bytearray(blob[:64])
 if len(h)!=64 or struct.unpack_from('>I',h)[0]!=0x27051956: raise ValueError('Invalid uImage')
 crc=struct.unpack_from('>I',h,4)[0];struct.pack_into('>I',h,4,0)
 if zlib.crc32(h)!=crc: raise ValueError('Header CRC mismatch')
 size=struct.unpack_from('>I',h,12)[0];payload=blob[64:]
 if len(payload)!=size or zlib.crc32(payload)!=struct.unpack_from('>I',h,24)[0]: raise ValueError('Payload CRC mismatch')
 length,term=struct.unpack_from('>II',payload)
 if term or length!=len(payload)-8: raise ValueError('Expected single script')
 script=payload[8:].decode();lines=script.splitlines(keepends=True)
 matches=[i for i,l in enumerate(lines) if re.match(r'\s*setenv bootargs ',l)]
 if len(matches)!=1: raise ValueError('Expected one bootargs assignment')
 i=matches[0];line=lines[i]
 line=re.sub(r'\s+console=\S+','',line)
 consoles={'dual':'console=ttyS0,115200 console=tty0','uart':'console=ttyS0,115200','hdmi':'console=tty0'}[mode]
 lines[i]=line.replace('setenv bootargs ','setenv bootargs '+consoles+' ',1)
 script=''.join(lines).encode();payload=struct.pack('>II',len(script),0)+script
 struct.pack_into('>I',h,12,len(payload));struct.pack_into('>I',h,24,zlib.crc32(payload));struct.pack_into('>I',h,4,zlib.crc32(h))
 return bytes(h)+payload
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--mode',choices=['dual','uart','hdmi'],default='dual');a=p.parse_args()
 with a.output.open('xb') as f:f.write(configure(a.source.read_bytes(),a.mode))
