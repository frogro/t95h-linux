#!/usr/bin/env python3
"""Resolve OpenWrt once, retaining the explicitly pinned T95H kernel."""
import argparse, datetime, hashlib, json, re, urllib.request
from pathlib import Path

def resolve(profile, console):
    repo=Path(__file__).resolve().parents[1]
    baseline=json.loads((repo/'boards/t95h/baseline.json').read_text())
    if profile not in baseline['profiles'] or console not in baseline['consoles']:
        raise ValueError('Unsupported profile or console')
    url='https://downloads.openwrt.org/.versions.json'
    with urllib.request.urlopen(url, timeout=30) as response:
        raw=response.read()
    version=json.loads(raw)['stable_version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Stable metadata contains no supported release version')
    return {
        'resolved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'openwrt':version, 'kernel':baseline['kernel'],
        'kernel_policy':baseline['kernel_policy'], 'baseline':baseline['id'],
        'profile':profile, 'console':console, 'comparison_build':False,
        'upstream_metadata':{url:hashlib.sha256(raw).hexdigest()},
        'full_source_lock_complete':False,
        'full_image_build_ready':baseline['full_image_build_ready'],
        'remaining':baseline['remaining'],
        'known_wlan_issue':baseline['wlan']['known_issue']
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--profile',choices=['base','base-A','base-B','base-A-B'],default='base-A-B')
    p.add_argument('--console',choices=['dual','hdmi','uart'],default='dual')
    a=p.parse_args(); result=resolve(a.profile,a.console)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
