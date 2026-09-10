#!/usr/bin/env python3
"""Resolve latest non-prerelease LibreELEC exactly once per build."""
import argparse,json,re,subprocess
from pathlib import Path

def resolve():
 release=json.loads(subprocess.check_output(['gh','api','repos/LibreELEC/LibreELEC.tv/releases/latest'],text=True))
 tag=release['tag_name']
 if release.get('draft') or release.get('prerelease') or not re.fullmatch(r'\d+\.\d+\.\d+',tag):raise ValueError('Expected stable LibreELEC release')
 obj=json.loads(subprocess.check_output(['gh','api','repos/LibreELEC/LibreELEC.tv/git/ref/tags/'+tag],text=True))['object']
 for _ in range(8):
  if obj['type']=='commit':break
  if obj['type']!='tag':raise ValueError('Unexpected tag object')
  obj=json.loads(subprocess.check_output(['gh','api','repos/LibreELEC/LibreELEC.tv/git/tags/'+obj['sha']],text=True))['object']
 if obj['type']!='commit' or not re.fullmatch('[0-9a-f]{40}',obj['sha']):raise ValueError('Cannot resolve immutable commit')
 return dict(repository='https://github.com/LibreELEC/LibreELEC.tv.git',tag=tag,commit=obj['sha'],profile='base-B',project='T95H',arch='aarch64',policy='latest stable resolved once; no fallback',release_url=release['html_url'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=resolve();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
