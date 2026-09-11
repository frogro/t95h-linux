#!/usr/bin/env python3
"""Create an isolated LibreELEC project from pinned sources and T95H locks."""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def gnu_mirror_urls(text):
 # ftpmirror recipes use both /package and /gnu/package paths.
 return re.sub(r'https?://ftpmirror\.gnu\.org/(?:gnu/)?', 'https://ftp.gnu.org/gnu/', text)
def wireguard_archive(text):
 # cgit regenerated this snapshot; archived bytes match all 123 tag files/modes.
 old='PKG_SHA256="6afe492647c3b0b2f68ab6df524e9e4290d03c34c3027e069e5bbc486949960e"'
 if 'PKG_VERSION="1.0.20250521"' not in text or old not in text:return text
 url='PKG_URL="https://git.zx2c4.com/wireguard-tools/snapshot/wireguard-tools-v${PKG_VERSION}.tar.xz"'
 if text.count(url)!=1:raise ValueError('WireGuard archive recipe changed; review required')
 return text.replace(url,'PKG_URL="https://sources.openwrt.org/wireguard-tools-${PKG_VERSION}.tar.xz"').replace(old,'PKG_SHA256="b6f2628b85b1b23cc06517ec9c74f82d52c4cdbd020f3dd2f00c972a1782950e"')
def config(text):
 out={}
 for l in text.splitlines():
  m=re.fullmatch(r'(CONFIG_\w+)=(.*)',l)
  if m: out[m[1]]=m[2]
  m=re.fullmatch(r'# (CONFIG_\w+) is not set',l)
  if m: out[m[1]]='n'
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--firmware',type=Path,required=True);p.add_argument('--request',type=Path,required=True);a=p.parse_args()
 le=a.source.resolve();board=ROOT/'boards/t95h';contract=json.loads((board/'libreelec/upstream.json').read_text());lock=json.loads(a.request.read_text())
 if subprocess.check_output(['git','rev-parse','HEAD'],cwd=le,text=True).strip()!=lock['commit']: raise ValueError('LibreELEC source revision mismatch')
 if subprocess.check_output(['git','status','--porcelain'],cwd=le): raise ValueError('LibreELEC checkout is not pristine')
 for name,expected in contract['adapter_source_contract'].items():
  if sha(le/name)!=expected:raise ValueError('Latest LibreELEC changed adapter input; review required, no fallback: '+name)
 pr=le/'projects/T95H';pr.mkdir()
 # Keep only explicit project defaults; no H6 ATF/Crust/bootloader or kernel patches.
 opts=(le/'projects/Allwinner/options').read_text()+'\n'+(le/'projects/Allwinner/devices/H6/options').read_text()
 opts+='''
# T95H adapter: boot media assembled separately using our locked prefix.
BOOTLOADER=""
UBOOT_FIRMWARE=""
ATF_PLATFORM=""
LINUX="t95h"
KERNEL_MAKE_EXTRACMD=""
GRAPHIC_DRIVERS="panfrost"
ADDITIONAL_PACKAGES="t95h-hardware"
FIRMWARE="misc-firmware wlan-firmware"
'''
 (pr/'options').write_text(opts)
 cfg=config((board/'profiles/kconfig-draft/base-B.config').read_text())
 # Preserve our hardware settings, add LE userspace requirements explicitly.
 required=['BLK_DEV_INITRD','DEVTMPFS','DEVTMPFS_MOUNT','TMPFS','TMPFS_POSIX_ACL','SQUASHFS','SQUASHFS_ZSTD','SQUASHFS_XZ','CGROUPS','CGROUP_PIDS','CGROUP_FREEZER','CGROUP_DEVICE','NAMESPACES','UTS_NS','IPC_NS','PID_NS','NET_NS','SECCOMP','SECCOMP_FILTER','FHANDLE','INOTIFY_USER','SIGNALFD','TIMERFD','EPOLL','UNIX','UNIX_DIAG','BINFMT_ELF','BINFMT_SCRIPT','BLK_DEV_LOOP','RD_GZIP','RD_ZSTD','ZSTD_DECOMPRESS','AUTOFS_FS','EXT4_FS','VFAT_FS','NLS_CODEPAGE_437','NLS_ISO8859_1']
 for key in required: cfg['CONFIG_'+key]='y'
 cfg.update(CONFIG_EXTRA_FIRMWARE='""',CONFIG_EXTRA_FIRMWARE_DIR='"firmware"',CONFIG_LOCALVERSION='"-t95h-libreelec"',CONFIG_LOCALVERSION_AUTO='n',CONFIG_INITRAMFS_SOURCE='""',CONFIG_INITRAMFS_ROOT_UID='0',CONFIG_INITRAMFS_ROOT_GID='0',CONFIG_INITRAMFS_COMPRESSION_ZSTD='y',CONFIG_INITRAMFS_COMPRESSION_NONE='n',CONFIG_MODULE_COMPRESS='n',CONFIG_MODULE_COMPRESS_XZ='n',CONFIG_MODULE_COMPRESS_ZSTD='n',CONFIG_MODULE_COMPRESS_GZIP='n')
 (pr/'linux').mkdir();(pr/'linux/linux.aarch64.conf').write_text('\n'.join(f'# {k} is not set' if v=='n' else f'{k}={v}' for k,v in sorted(cfg.items()))+'\n')
 kl=json.loads((board/'kernel/source-lock.json').read_text());bl=json.loads((board/'baseline.json').read_text());w=bl['wlan']
 patches=[(board/'kernel'/kl['patch'],kl['patch_sha256']),(board/w['incremental_patch'],w['incremental_patch_sha256'])]+[(board/x['path'],x['sha256']) for x in w['followup_patches']]
 dest=pr/'patches/linux';dest.mkdir(parents=True)
 for n,(s,h) in enumerate(patches):
  if sha(s)!=h:raise ValueError('Hardware patch changed')
  shutil.copyfile(s,dest/f'{n:04}-t95h.patch')
 pkg=le/'packages/linux/package.mk';s=pkg.read_text();marker='case "${LINUX}" in\n';assert s.count(marker)==1
 case=f'''  t95h)
    PKG_VERSION="{bl['kernel']}"
    PKG_SHA256="{kl['archive_sha256']}"
    PKG_URL="https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-${{PKG_VERSION}}.tar.xz"
    PKG_PATCH_DIRS="t95h"
    ;;
''';pkg.write_text(s.replace(marker,marker+case))
 kodi=le/'packages/mediacenter/kodi/package.mk';ks=kodi.read_text();ks=ks.replace('[ "${PROJECT}" = "Allwinner" -o', '[ "${PROJECT}" = "T95H" -o "${PROJECT}" = "Allwinner" -o');kodi.write_text(ks)
 for package in ('glibc','gcc','systemd'):
  shutil.copytree(board/'libreelec/patches'/package,pr/'patches'/package)
 # Avoid random GNU redirect mirrors; package versions and hashes remain upstream.
 for recipe in (le/'packages').rglob('package.mk'):
  text=recipe.read_text();fixed=gnu_mirror_urls(text)
  if fixed!=text:recipe.write_text(fixed)
 # Linux 7.2.3 exports a kernel-only counted_by annotation in vhost_types.h.
 # Strip only that annotation from installed userspace headers, not kernel source.
 linux_recipe=le/'packages/linux/package.mk';ls=linux_recipe.read_text()
 anchor='    headers_install\n'
 if ls.count(anchor)!=1:raise ValueError('Linux header export recipe changed')
 sanitize="    sed -i 's/ __counted_by(count)//g' dest/include/linux/vhost_types.h\n"
 linux_recipe.write_text(ls.replace(anchor,anchor+sanitize))
 # Savannah redirector returns 502 for attr; use its direct archive mirror.
 attr=le/'packages/devel/attr/package.mk';ats=attr.read_text()
 attr.write_text(ats.replace('http://download.savannah.nongnu.org/releases/attr/', 'https://download-mirror.savannah.gnu.org/releases/attr/'))
 wg=le/'packages/network/wireguard-tools/package.mk';wg.write_text(wireguard_archive(wg.read_text()))
 # Same GMP archive from GNU; keep upstream version and SHA256 verification.
 gmp=le/'packages/devel/gmp/package.mk';gs=gmp.read_text();gmp.write_text(gs.replace('https://gmplib.org/download/gmp/', 'https://ftp.gnu.org/gnu/gmp/'))
 stage=le/'t95h-startup';subprocess.run(['/usr/bin/python3',str(ROOT/'tools/stage-startup-fixes.py'),'--profile','base-B','--output',str(stage)],check=True)
 hw=pr/'packages/t95h-hardware';shutil.copytree(board/'libreelec/hardware',hw)
 src=hw/'sources';src.mkdir();shutil.copyfile(board/'external/regulator/t95h_aldo2.c',src/'t95h_aldo2.c');shutil.copyfile(stage/'ana/t95h_ana_provider.c',src/'t95h_ana_provider.c');(src/'Makefile').write_text('obj-m := t95h_aldo2.o t95h_ana_provider.o\n');shutil.copyfile(stage/'t95h.dtb',hw/'t95h.dtb')
 firmware=hw/'firmware';firmware.mkdir();selected={}
 for entry in json.loads((board/'profiles/integration-draft.json').read_text())['firmware']:
  if entry['profile'] not in ('base','B'):continue
  rel=entry['file'];f=a.firmware/rel
  if sha(f)!=entry['sha256']:raise ValueError('Firmware hash mismatch: '+rel)
  out=firmware/rel.removeprefix('lib/firmware/');out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,out);selected[rel]=sha(f)
 report={'upstream':lock,'kernel':bl['kernel'],'kernel_patches':[sha(x[0]) for x in patches],'profile':'base-B','firmware':selected,'hardware_tested':False,'bootloader_rebuilt':False,'image_ready':False,'required_kernel_config':required,'excluded_allwinner_kernel_patches':sorted(p.name for p in (le/'projects/Allwinner/patches/linux').glob('*.patch'))}
 (le/'t95h-port.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS: LibreELEC T95H source project prepared; no image built yet')
if __name__=='__main__':main()
