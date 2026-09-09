#!/usr/bin/env python3
"""Read-only evidence inventory; no kernel/config changes or profile builds."""
from pathlib import Path
import json,re,hashlib,subprocess
P=Path(__file__).resolve().parents[2];O=P/'outputs/profile-audit';R=P/'outputs/cedrus-hdmi-fixed/A/root';K=P/'build/work/next-cedrus-A';IB=P/'build/tools/openwrt-imagebuilder-25.12.5-sunxi-cortexa53.Linux-x86_64'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(O/n).write_text(json.dumps(v,indent=2)+'\n')
def cfg(p):
 d={}
 for l in p.read_text().splitlines():
  if l.startswith('CONFIG_') and '=' in l:k,v=l.split('=',1);d[k]=v
  elif l.startswith('# CONFIG_') and l.endswith(' is not set'):d[l.split()[1]]='n'
 return d
assert sha(O/'kernel.config')==sha(K/'.config')
assert sha(O/'installed')==sha(R/'lib/apk/db/installed'),'Artifact APK inventory differs from backup'
pkgs={};providers={}
for block in (O/'installed').read_text().split('\n\n'):
 d={l[0]:l[2:] for l in block.splitlines() if len(l)>1 and l[1]==':' and l[0] in 'PVDp'}
 if 'P' not in d:continue
 name=d['P'];pkgs[name]=d
 providers[name]=name
 for v in d.get('p','').split():providers[re.split('[=<>~]',v)[0]]=name
def resolve(n):return providers.get(re.split('[=<>~]',n)[0])
def closure(seeds):
 seen=set();missing=set();todo=list(seeds)
 while todo:
  n=todo.pop()
  if n.startswith('!'):continue
  match=resolve(n)
  if not match:missing.add(n);continue
  if match in seen:continue
  seen.add(match);todo.extend(pkgs[match].get('D','').split())
 return seen,sorted(missing)
defaults=re.search(r'^Default Packages: (.*)$',(O/'imagebuilder-info.txt').read_text(),re.M)[1].split()
replacements={'dnsmasq':'dnsmasq-full','nftables':'nftables-json'}
base=[replacements.get(n,n) for n in defaults]+['t95h-kernel','luci-ssl','luci-app-ttyd','wpad-basic-mbedtls','wifi-scripts','wireless-regdb','alsa-utils','usbutils','ethtool','ip-full','iw-full','iputils-ping','curl','nano','htop','block-mount','lm-sensors','socat','coreutils-od','openssl-util']
a=['modemmanager','modemmanager-rpcd','luci-proto-modemmanager','luci-proto-mbim','luci-proto-qmi','mbim-utils','umbim','uqmi','usb-modeswitch']
b=['libmesa-panfrost','kmscube','gstreamer1-plugins-base']+json.loads((P/'t95h-linux/boards/t95h/profiles/streaming-packages-draft.json').read_text())['extra_seeds']
sets={};missing={}
for label,seeds in [('base',base),('A',a),('B',b)]:sets[label],missing[label]=closure(seeds)
rows=[]
for name,d in sorted(pkgs.items()):
 need=[label for label,s in sets.items() if name in s]
 category='base' if 'base' in need else '+'.join(need) if need else 'review'
 rows.append({'name':name,'version':d.get('V'),'profile':category,'needed_by':need,'dependencies':d.get('D','').split()})
write('packages.json',{'official_target_defaults':defaults,'replacements':replacements,'seeds':{'base':base,'A':a,'B':b},'missing_dependencies_or_defaults':missing,'packages':rows,'note':'Installed t95h-kernel is monolithic and supplies virtual kmods; profile-specific provides must be regenerated, not copied blindly.'})
cur=cfg(O/'kernel.config');official=cfg(IB/'target/linux/generic/config-6.12');official.update(cfg(IB/'target/linux/sunxi/config-6.12'));official.update(cfg(IB/'target/linux/sunxi/cortexa53/config-6.12'))
gaps=[{'symbol':k,'openwrt_fragment':v,'current':cur.get(k,'absent')} for k,v in official.items() if v in ['y','m'] and cur.get(k) not in ['y','m']]
write('kernel-fragment-gaps.json',{'warning':'Fragment comparison is a review list, not a resolved standard image Kconfig. Version-renamed/removed symbols and unrelated SoCs must be checked, not enabled blindly.','gaps':gaps})
mods=R/'lib/modules/7.2.3-t95h-candidate3';actual={p.name for p in mods.glob('*.ko')};ordered={Path(x).name.removesuffix('.o')+'.ko' for x in (K/'modules.order').read_text().splitlines()}
mrows=[]
for f in sorted(R.rglob('*.ko')):
 n=f.name;group='A' if n.startswith(('mt76','mt79','rtw88')) else 'B' if n.startswith(('sunxi-cedrus','videobuf2','v4l2-')) else 'base'
 r=subprocess.run(['modinfo','-F','depends',str(f)],capture_output=True,text=True)
 mrows.append({'file':str(f.relative_to(R)),'profile':('B' if 't95h_ana_provider' in n else group),'sha256':sha(f),'depends':r.stdout.strip().split(',') if r.stdout.strip() else [],'modinfo_rc':r.returncode})
write('modules.json',{'config_sha256':sha(O/'kernel.config'),'built_not_shipped':sorted(ordered-actual),'external_or_not_in_modules_order':sorted(actual-ordered),'modules':mrows,'builtin_note':'Built-in drivers are inventoried by kernel.config. Panfrost and several modem drivers are built-in; packages alone cannot implement profile toggles.'})
fw=[]
for f in sorted((R/'lib/firmware').rglob('*')):
 if f.is_dir():continue
 n=str(f.relative_to(R/'lib/firmware'));group='base' if n.startswith(('xr819','regulatory')) else 'A' if n.startswith(('mediatek','rtw88','mt7662')) else 'review'
 fw.append({'file':str(f.relative_to(R)),'profile':('B' if 't95h_ana_provider' in n else group),'symlink':str(f.readlink()) if f.is_symlink() else None,'target_exists':f.exists(),'sha256':sha(f) if f.exists() and f.is_file() else None})
write('firmware.json',fw)
patches=sorted((P/'patches').rglob('*.patch'))+sorted((P/'outputs/next-cedrus/upstream').glob('*.patch'))+sorted((P/'outputs/next-fat-pwm8/upstream/display-patches').glob('*.patch'))+list((P/'sources/board/t95h-ppu-fix').glob('*.patch'))+list((P/'outputs/next-fat-pwm8').glob('audio.patch'))
pr=[]
for f in patches:
 text=f.read_text(errors='replace');r=subprocess.run(['patch','--force','--fuzz=0','--dry-run','--reverse','-p1','-d',str(K/'drivers/net/wireless/xradio' if f.name=='xradio-linux72-build.patch' else K)],input=text,capture_output=True,text=True,timeout=30)
 subject=re.search(r'^Subject: (.*)',text,re.M)
 pr.append({'path':str(f.relative_to(P)),'sha256':sha(f),'subject':subject[1] if subject else f.name,'files':re.findall(r'^\+\+\+ b/(.*)$',text,re.M),'reverse_check':'exact_reverse_possible' if r.returncode==0 else 'review_superseded_or_different_context','returncode':r.returncode,'output':(r.stdout+r.stderr)[-4000:]})
write('patches.json',{'tree':str(K.relative_to(P)),'warning':'Reverse dry-run success proves current hunk context only. Failure does not prove patch absence. Series order and manual edits require explicit reconciliation. No files changed.','patches':pr})
print(json.dumps({'packages':len(rows),'unassigned_packages':[r['name'] for r in rows if r['profile']=='review'],'missing':missing,'module_count':len(mrows),'built_not_shipped':sorted(ordered-actual),'firmware_files':len(fw),'kernel_fragment_review':len(gaps),'patches':len(pr),'patch_reverse_exact':sum(r['returncode']==0 for r in pr)},indent=2))
