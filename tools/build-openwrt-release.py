#!/usr/bin/env python3
"""Build one selected profile and its install/sysupgrade pair on a clean runner."""
import argparse,hashlib,json,os,re,shutil,subprocess,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(*cmd):
 print('+',*(str(x) for x in cmd),flush=True);subprocess.run(list(map(str,cmd)),check=True,cwd=ROOT)
def get(url,p):
 with urllib.request.urlopen(url,timeout=120) as r,p.open('wb') as f:shutil.copyfileobj(r,f)
def main():
 p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--sign-key',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--jobs',type=int,default=2);p.add_argument('--revision',type=int,required=True);a=p.parse_args()
 if a.revision<1:raise ValueError('Positive package revision required')
 o=a.output.resolve();o.mkdir(exist_ok=False,parents=True);request=json.loads(a.request.read_text());lock=json.loads((ROOT/'boards/t95h/build-inputs.json').read_text());epoch=str(lock['epoch']);os.environ['SOURCE_DATE_EPOCH']=epoch
 if sha(a.inputs)!=lock['sha256']:raise ValueError('Build input checksum mismatch')
 with tarfile.open(a.inputs) as t:t.extractall(o/'inputs',filter='data')
 inputs=o/'inputs';tc=inputs/'toolchain';fw=inputs/'firmware';prefix=inputs/'prefix.bin'
 if sha(prefix)!=lock['boot_prefix_sha256']:raise ValueError('Boot prefix mismatch')
 version=request['openwrt']
 if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid release')
 url=f'https://downloads.openwrt.org/releases/{version}/targets/sunxi/cortexa53/'
 get(url+'sha256sums',o/'upstream-sha256sums')
 entries={line.split()[-1].lstrip('*'):line.split()[0] for line in (o/'upstream-sha256sums').read_text().splitlines() if len(line.split())==2}
 names=[n for n in entries if n.startswith(f'openwrt-imagebuilder-{version}-sunxi-cortexa53.Linux-x86_64.tar.')]
 if len(names)!=1:raise ValueError('No unique matching ImageBuilder')
 name=names[0];get(url+name,o/name)
 if sha(o/name)!=entries[name]:raise ValueError('ImageBuilder checksum mismatch')
 run('tar','-xf',o/name,'-C',o)
 ib=o/f'openwrt-imagebuilder-{version}-sunxi-cortexa53.Linux-x86_64'
 keys=o/'keys';shutil.copytree(ib/'keys',keys)
 run('openssl','pkey','-in',a.sign_key.resolve(),'-pubout','-out',keys/'t95h-build.pem')
 py='/usr/bin/python3'
 def tool(name,*args):run(py,ROOT/'tools'/name,*args)
 tool('download-kernel-archive.py','--output',o/'kernel.tar.xz')
 tool('prepare-kernel-source.py','--archive',o/'kernel.tar.xz','--output',o/'source')
 tool('build-profile-kernel.py','--source-stage',o/'source','--toolchain',tc,'--firmware-root',fw,'--profile',request['profile'],'--output',o/'kernel','--jobs',a.jobs,'--epoch',epoch)
 tool('build-profile-modules.py','--kernel-build',o/'kernel','--toolchain',tc,'--output',o/'modules','--jobs',a.jobs,'--epoch',epoch)
 tool('package-profile-kernel.py','--kernel-build',o/'kernel','--modules-stage',o/'modules','--firmware-root',fw,'--imagebuilder',ib,'--sign-key',a.sign_key.resolve(),'--keys',keys,'--output',o/'kernel-package','--version','7.2.3-r'+str(a.revision),'--epoch',epoch)
 pkg=json.loads((o/'kernel-package/package-report.json').read_text())
 tool('assemble-openwrt-packages.py','--request',a.request.resolve(),'--imagebuilder',ib,'--keys',keys,'--kernel-package',o/'kernel-package'/pkg['package'],'--kernel-sha256',pkg['sha256'],'--output',o/'packages')
 tool('prepare-openwrt-rootfs.py','--packages',o/'packages','--imagebuilder',ib,'--compiler',tc/'bin/aarch64-openwrt-linux-musl-gcc','--output',o/'rootfs','--epoch',epoch)
 tool('assemble-profile-image.py','--rootfs-stage',o/'rootfs','--prefix',prefix,'--imagebuilder',ib,'--output',o/'image','--console',request['console'],'--epoch',epoch)
 img=json.loads((o/'image/image-report.json').read_text())
 tool('package-openwrt-upgrade.py','--image',o/'image/t95h-base.img','--sha256',img['sha256'],'--output',o/'release','--fwtool',ib/'staging_dir/host/bin/fwtool','--profile',request['profile'])
 tool('test-openwrt-upgrade.py','--build',o/'release')
 for source,name in [(a.request,'request.json'),(o/'packages/package-lock.json','package-lock.json'),(o/'kernel-package/package-report.json','kernel-package-report.json')]:shutil.copyfile(source,o/'release'/name)
 notes=f'''# T95H {request['profile']}: OpenWrt {version}, Linux {request['kernel']}

Install image and matching sysupgrade from one build. Console: {request['console']}.
Kernel and boot chain remain pinned; OpenWrt stable was resolved once for this run.
Base includes HDMI console/audio, internal WLAN, Ethernet, IR and frontdisplay.
Profile A adds the selected USB network/modem support; B adds GPU/media support.
Actual packages and firmware are recorded in package-lock.json and kernel-package-report.json.

Experimental SD rescan: up to three boot payload load attempts. Two successful
cold starts were reported after the change; general coldboot reliability is not proven.
Known WLAN SDIO errors, GPU initialization and audio hardware validation remain
open/documented. No new hardware, listening or stress tests are implied.
Default access: root / openwrt; AP openwrt / openwrtopenwrt. Change these credentials.
Public source-complete redistribution of the binary boot/toolchain/firmware inputs
requires the remaining provenance/license work. This is a private test artifact.
'''
 (o/'release/RELEASE-NOTES.md').write_text(notes)
 print('PASS: selected-profile install and sysupgrade complete; hardware limitations documented',flush=True)
if __name__=='__main__':main()
