"""Validate downloaded install/sysupgrade checksums before offering a flash step."""
import hashlib,re
from pathlib import Path

def verify(directory):
 directory=Path(directory).resolve();manifests=list(directory.rglob('SHA256SUMS'))
 if len(manifests)!=1:raise ValueError('Expected one release SHA256SUMS')
 manifest=manifests[0];checked=[]
 for line in manifest.read_text().splitlines():
  if not line.strip():continue
  match=re.fullmatch(r'([0-9a-f]{64})\s+\*?([^/\\]+)',line)
  if not match or match[2] in ('.','..'):raise ValueError('Invalid checksum manifest entry')
  path=manifest.parent/match[2]
  if path.is_symlink() or not path.is_file():raise ValueError('Missing or linked artifact: '+match[2])
  with path.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
  if actual!=match[1]:raise ValueError('Artifact SHA256 mismatch: '+match[2])
  checked.append(path.name)
 if not any(x.endswith('-install.img') for x in checked) or not any(x.endswith('-sysupgrade.bin') for x in checked):raise ValueError('Install/sysupgrade pair missing from manifest')
 return checked
