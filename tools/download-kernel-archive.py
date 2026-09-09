#!/usr/bin/env python3
"""Download only the repository-pinned kernel archive and verify its SHA256."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
lock=json.loads((ROOT/'boards/t95h/kernel/source-lock.json').read_text())
match=re.fullmatch(r'linux-(\d+)\.(\d+)\.(\d+)\.tar\.xz',lock['archive'])
if not match:raise ValueError('Invalid locked kernel archive name')
url='https://cdn.kernel.org/pub/linux/kernel/v'+match[1]+'.x/'+lock['archive']
a.output.parent.mkdir(parents=True,exist_ok=True)
# Exclusive output: a failed download remains identifiable, never silently reused.
digest=hashlib.sha256()
with a.output.open('xb') as target,urllib.request.urlopen(url,timeout=60) as response:
 while chunk:=response.read(1024*1024):target.write(chunk);digest.update(chunk)
if digest.hexdigest()!=lock['archive_sha256']:raise ValueError('Kernel download checksum mismatch; do not extract')
with a.output.open('rb') as stream:
 if hashlib.file_digest(stream,'sha256').hexdigest()!=lock['archive_sha256']:raise ValueError('Saved archive checksum mismatch')
print('PASS:',lock['archive'],lock['archive_sha256'])
