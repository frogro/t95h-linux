#!/usr/bin/env python3
"""Replay the locked T95H kernel source from a pristine archive, once.

No previous build tree, hardware access, kernel compilation or extra A/B run.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]

def sha(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--archive',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();archive=a.archive.resolve(strict=True)
 board=ROOT/'boards/t95h';lock=json.loads((board/'kernel/source-lock.json').read_text())
 baseline=json.loads((board/'baseline.json').read_text());w=baseline['wlan']
 if sha(archive)!=lock['archive_sha256']:raise ValueError('Kernel archive hash mismatch')
 patches=[(board/'kernel'/lock['patch'],lock['patch_sha256']),
          (board/w['incremental_patch'],w['incremental_patch_sha256'])]
 for path,digest in patches:
  if sha(path)!=digest:raise ValueError('Patch hash mismatch: '+str(path))
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 prefix='linux-'+baseline['kernel'];tree=out/prefix
 def checked_filter(member,destination):
  parts=PurePosixPath(member.name).parts
  if not parts or parts[0]!=prefix or '..' in parts:raise ValueError('Unexpected archive path')
  return tarfile.data_filter(member,destination)
 print('Extracting verified kernel archive into:',tree,flush=True)
 with tarfile.open(archive) as bundle:bundle.extractall(out,filter=checked_filter)
 if not tree.is_dir():raise ValueError('Expected kernel root missing')
 with (out/'patch.log').open('w') as log:
  for index,(patch,_) in enumerate(patches):
   subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1','-i',str(patch)],cwd=tree,stdout=log,stderr=subprocess.STDOUT,check=True)
   if index==0:
    for entry in lock['files']:
     path=tree/entry['path']
     if sha(path)!=entry['sha256']:raise ValueError('Consolidated replay differs: '+entry['path'])
 # The incremental patch changes exactly the two reviewed source files.
 changed={'drivers/net/wireless/xradio/hwio.c','drivers/net/wireless/xradio/hwio.h'}
 for entry in lock['files']:
  if entry['path'] not in changed and sha(tree/entry['path'])!=entry['sha256']:
   raise ValueError('Unexpected incremental change: '+entry['path'])
 if sha(archive)!=lock['archive_sha256']:raise ValueError('Archive changed during extraction')
 result={'source_preparation_passed':True,'kernel_compiled':False,'previous_tree_used':False,
         'kernel':baseline['kernel'],'archive_sha256':lock['archive_sha256'],
         'patches':[{'path':str(path.relative_to(ROOT)),'sha256':digest} for path,digest in patches],
         'verified_consolidated_files':len(lock['files']),
         'incremental_files':{name:sha(tree/name) for name in sorted(changed)},
         'remaining':['Profile config, embedded firmware and toolchain','Kernel and external module compilation']}
 (out/'source-report.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS: locked source replay including incremental WLAN read-size fix.')
if __name__=='__main__':main()
