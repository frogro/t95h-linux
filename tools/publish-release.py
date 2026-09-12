#!/usr/bin/env python3
"""Publish one verified SD image pair as an experimental GitHub prerelease."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
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
        if installer.get('metadata_helper_runtime_verified') is not True or installer.get('payload_readback_verified') is not True or installer.get('sha256')!=digest:raise ValueError('Installer verification mismatch')
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
    paths.update([directory/'SHA256SUMS',directory/'RELEASE-NOTES.md',directory/'t95h-keep'])
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
    feed=a.directory/'module-feed.json'
    tag=f't95h-feedtest-{a.run_id}-{a.attempt}' if feed.exists() else f't95h-{a.run_id}-{a.attempt}'
    if feed.exists():
        proof=json.loads(feed.read_text())
        if not proof.get('apk_http_install_remove_verified') or not proof.get('wrong_kernel_abi_rejected') or not proof.get('untrusted_index_rejected'):
            raise ValueError('Feed checks incomplete')
        if proof['url'].split('/')[-1]!=tag:raise ValueError('Feed release tag mismatch')
    repo=subprocess.check_output(['gh','repo','view','--json','nameWithOwner','--jq','.nameWithOwner'],text=True).strip()
    found=subprocess.run(['gh','release','view',tag,'--json','apiUrl'],capture_output=True,text=True)
    if found.returncode:
        if 'release not found' not in found.stderr.lower():raise RuntimeError(found.stderr)
        subprocess.run(['gh','release','create',tag,'--target',a.commit,'--draft','--prerelease',
                        '--title',f'T95H {a.profile} / {a.console} — experimental build {a.run_id}',
                        '--notes-file',str(a.directory/'RELEASE-NOTES.md')],check=True)
        found=subprocess.run(['gh','release','view',tag,'--json','apiUrl'],capture_output=True,text=True,check=True)
    api_url=json.loads(found.stdout)['apiUrl']
    release=json.loads(subprocess.check_output(['gh','api',api_url]))
    if not release['draft']:raise ValueError('Release already published; refusing mutation')
    pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp',f"repos/{repo}/releases/{release['id']}/assets?per_page=100"]))
    existing={item['name']:item for page in pages for item in page}
    expected={path.name for path in files}
    if set(existing)-expected:raise ValueError('Unexpected assets in draft')
    pending=[]
    for path in files:
        with path.open('rb') as f:digest='sha256:'+hashlib.file_digest(f,'sha256').hexdigest()
        if path.name in existing:
            if existing[path.name].get('digest')!=digest:raise ValueError('Existing asset checksum mismatch: '+path.name)
        else:pending.append(path)
    print(f'Resuming draft: {len(existing)} verified assets, {len(pending)} pending',flush=True)
    for index,path in enumerate(pending):
        for retry in range(4):
            result=subprocess.run(['gh','release','upload',tag,str(path)],capture_output=True,text=True)
            if result.returncode==0:break
            if 'secondary rate limit' not in result.stderr and '429' not in result.stderr:raise RuntimeError(result.stderr)
            if retry==3:raise RuntimeError('Rate limit persists; verified draft retained for resume')
            time.sleep(60*(retry+1))
        if len(files)>100:time.sleep(10)
        if index%20==0:print(f'Uploaded {index+1}/{len(pending)} remaining assets',flush=True)
    subprocess.run(['gh','release','edit',tag,'--draft=false','--prerelease','--latest=false'],check=True)
    print('PASS: experimental release published:',tag)
if __name__=='__main__':main()
