#!/usr/bin/env python3
"""Execute the extracted ARM64 metadata helper before publishing an installer."""
import argparse, os, shutil, stat, subprocess, tempfile
from pathlib import Path

def check(binary):
 qemu=shutil.which('qemu-aarch64-static') or shutil.which('qemu-aarch64')
 if not qemu: raise RuntimeError('ARM64 metadata verification requires qemu-user')
 with tempfile.TemporaryDirectory() as d:
  p=Path(d);f=p/'file';f.write_text('fixture');f.chmod(0o600)
  (p/'link').symlink_to('file')
  for path in (f,p,p/'link'):
   s=path.lstat();expected=f'{stat.S_IMODE(s.st_mode):o}:{s.st_uid}:{s.st_gid}'
   r=subprocess.run([qemu,str(binary),str(path)],capture_output=True,text=True,timeout=20)
   if r.returncode or r.stdout.strip()!=expected: raise RuntimeError('ARM64 metadata result mismatch: '+r.stderr)
  r=subprocess.run([qemu,str(binary),str(p/'missing')],capture_output=True,timeout=20)
  if r.returncode==0: raise RuntimeError('Missing path incorrectly accepted')
 print('PASS: extracted ARM64 metadata helper: file/directory/symlink/missing path')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('binary',type=Path);a=p.parse_args();check(a.binary.resolve())
