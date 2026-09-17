#!/usr/bin/python3
"""Compare installer configuration snapshots: compare names, types, symlinks and bytes."""
import os,sys,stat
from pathlib import Path
def equal(a,b):
 try:
  sa=a.lstat();sb=b.lstat()
  if stat.S_IFMT(sa.st_mode)!=stat.S_IFMT(sb.st_mode):return False
  if a.is_symlink():return os.readlink(a)==os.readlink(b)
  if a.is_dir():
   names=set(os.listdir(a))
   return names==set(os.listdir(b)) and all(equal(a/n,b/n) for n in names)
  if a.is_file():
   if sa.st_size!=sb.st_size:return False
   with a.open('rb') as fa,b.open('rb') as fb:
    while True:
     x=fa.read(1048576);y=fb.read(1048576)
     if x!=y:return False
     if not x:return True
  return False
 except OSError:return False
if __name__=='__main__':
 if sys.argv[1:]==['--check']:sys.exit(0)
 if len(sys.argv)!=4 or sys.argv[1]!='-r':sys.exit('Only diff -r DIR DIR is supported')
 if not equal(Path(sys.argv[2]),Path(sys.argv[3])):
  print('Configuration contents differ:',sys.argv[2],sys.argv[3],file=sys.stderr);sys.exit(1)
