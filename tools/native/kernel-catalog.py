#!/usr/bin/env python3
"""Select the native OpenWrt kmod catalog and export only ABI-matched APKs."""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path
R=Path(__import__('os').environ['NATIVE_WORK']); S=R/'source'
p=argparse.ArgumentParser(); p.add_argument('mode',choices=['configure','audit','export']); a=p.parse_args()
if a.mode=='configure':
 c=S/'.config'; t=c.read_text()
 t=re.sub(r'^# CONFIG_PACKAGE_kmod-.* is not set\n','',t,flags=re.M)
 t=re.sub(r'^(?:# CONFIG_ALL_KMODS is not set|CONFIG_ALL_KMODS=.*)\n','',t,flags=re.M)
 c.write_text(t+'\nCONFIG_ALL_KMODS=y\n')
 subprocess.run(['make','defconfig'],cwd=S,check=True)
c=(S/'.config').read_text(); selected=dict(re.findall(r'^CONFIG_PACKAGE_(kmod-[^=]+)=([ym])$',c,re.M))
if 'CONFIG_ALL_KMODS=y' not in c: raise SystemExit('ALL_KMODS is required')
metadata={}
for block in (S/'tmp/.packageinfo').read_text().split('\nPackage: '):
 if not block.startswith('kmod-'):continue
 name=block.splitlines()[0]
 metadata[name]={key:(re.search(r'^'+key+r': (.*)$',block,re.M).group(1) if re.search(r'^'+key+r': (.*)$',block,re.M) else '') for key in ['Depends','Menu-Depends','Conflicts']}
report={'selection':'OpenWrt ALL_KMODS, target dependencies enforced by Kconfig',
 'selected':selected,'image_count':sum(v=='y' for v in selected.values()),'feed_only_count':sum(v=='m' for v in selected.values()),
 'not_selected':{n:d for n,d in metadata.items() if n not in selected},'packages_verified':False}
if a.mode=='export':
 apk=S/'staging_dir/host/bin/apk'
 kernels=list((S/'build_dir/target-aarch64_cortex-a53_musl/linux-sunxi_cortexa53').glob('linux-*/include/config/kernel.release'))
 if len(kernels)!=1:raise SystemExit('Ambiguous kernel build')
 k=kernels[0].parents[2]; version=kernels[0].read_text().strip(); abi=(k/'.vermagic').read_text().strip()
 tag=f"native-kmods-{version}-{abi}-{__import__('os').environ['T95H_FEED_ID']}"; out=R/'releases'/tag
 found={}; expected=f'kernel={version}~{abi}-r1'
 for f in sorted((S/'bin').rglob('kmod-*.apk')):
  info=json.loads(subprocess.check_output([str(apk),'adbdump','--format','json',str(f)],text=True))['info']
  name=info['name']
  if name not in selected:continue
  if expected not in info.get('depends',[]):raise SystemExit('Stale/wrong kernel ABI: '+str(f))
  digest=hashlib.sha256(f.read_bytes()).hexdigest()
  if name in found and found[name]['sha256']!=digest:raise SystemExit('Different duplicate package: '+name)
  found[name]={'source':str(f),'filename':name+'.apk','sha256':digest}
 missing=sorted(set(selected)-set(found))
 if missing:raise SystemExit('Catalog incomplete: '+', '.join(missing))
 if out.exists():
  old=json.loads((out/'catalog.json').read_text())
  old_hashes={n:v['sha256'] for n,v in old['packages'].items()}
  new_hashes={n:v['sha256'] for n,v in found.items()}
  if old_hashes!=new_hashes:
   raise SystemExit('ABI repository already exists with different package contents; refusing mutable feed')
  for entry in found.values():
   if hashlib.sha256((out/entry['filename']).read_bytes()).hexdigest()!=entry['sha256']:
    raise SystemExit('Existing repository integrity failure')
  (R/'logs/full-kernel-catalog.json').write_text(json.dumps(old,indent=2)+'\n')
  print('PASS: existing identical signed ABI repository reused: '+tag)
  raise SystemExit(0)
 out.mkdir(parents=True)
 for entry in found.values():shutil.copy2(entry['source'],out/entry['filename'])
 subprocess.run([str(apk),'mkndx','--allow-untrusted','--sign-key',str(S/'private-key.pem'),'--pkgname-spec','${name}.apk','--output',str(out/'packages.adb')]+[str(x) for x in sorted(out.glob('*.apk'))],check=True)
 shutil.copy2(S/'public-key.pem',out/'public-key.pem')
 report.update(packages_verified=True,kernel_dependency=expected,release_tag=tag,packages=found)
 (out/'catalog.json').write_text(json.dumps(report,indent=2)+'\n')
 (out/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file()))
(R/'logs/full-kernel-catalog.json').write_text(json.dumps(report,indent=2)+'\n')
print(f"Selected: {len(selected)}; image: {report['image_count']}; feed: {report['feed_only_count']}; not selected: {len(report['not_selected'])}; APKs verified: {report['packages_verified']}")
