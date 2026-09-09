#!/usr/bin/env python3
"""Publish one verified SD image pair as an experimental GitHub prerelease."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'installer'))
from verify_release import verify

def assets(directory, profile, console):
    directory=Path(directory)
    checked=verify(directory)
    request=json.loads((directory/'request.json').read_text())
    if request['profile']!=profile or request['console']!=console:
        raise ValueError('Requested profile/console does not match build')
    bundle=directory/'release-set.json'
    if bundle.exists():
        roles=json.loads(bundle.read_text())['artifacts']
        reports=[(directory/'sd-upgrade-test.json',roles['sd_upgrade']),(directory/'emmc-upgrade-test.json',roles['emmc_upgrade'])]
        installer=json.loads((directory/'installer-proof.json').read_text())
        with (directory/roles['sd_emmc_installer']).open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        if installer.get('payload_readback_verified') is not True or installer.get('sha256')!=digest:raise ValueError('Installer verification mismatch')
    else:
        images=[x for x in checked if x.endswith('-sysupgrade.bin')]
        installs=[x for x in checked if x.endswith('-install.img')]
        if len(images)!=1 or len(installs)!=1:raise ValueError('Expected exactly one image pair')
        reports=[(directory/'upgrade-test.json',images[0])]
    for report,image in reports:
        proof=json.loads(report.read_text())
        with (directory/image).open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        if proof.get('passed') is not True or proof.get('sysupgrade_sha256')!=digest:
            raise ValueError('Upgrade tests do not cover this payload')
    paths={directory/x for x in checked}
    paths.update(directory.glob('*.json'))
    paths.update([directory/'SHA256SUMS',directory/'RELEASE-NOTES.md',directory/'t95h-keep',ROOT/'installer.sh'])
    for path in paths:
        if path.is_symlink() or not path.is_file():raise ValueError('Missing/linked release asset: '+str(path))
    return sorted(paths)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--profile',required=True,choices=['base','base-A','base-B','base-A-B'])
    p.add_argument('--console',required=True,choices=['dual','hdmi','uart'])
    p.add_argument('--run-id',required=True,type=int)
    p.add_argument('--attempt',required=True,type=int)
    p.add_argument('--commit',required=True)
    a=p.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',a.commit):raise ValueError('Full source commit required')
    files=assets(a.directory,a.profile,a.console)
    # Each run attempt has its own immutable asset set. Failed uploads stay draft.
    tag=f't95h-{a.run_id}-{a.attempt}'
    subprocess.run(['gh','release','create',tag,'--target',a.commit,'--draft','--prerelease',
                    '--title',f'T95H {a.profile} / {a.console} — experimental build {a.run_id}',
                    '--notes-file',str(a.directory/'RELEASE-NOTES.md')],check=True)
    subprocess.run(['gh','release','upload',tag,*map(str,files)],check=True)
    subprocess.run(['gh','release','edit',tag,'--draft=false','--prerelease','--latest=false'],check=True)
    print('PASS: experimental release published:',tag)
if __name__=='__main__':main()
