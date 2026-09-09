#!/usr/bin/env python3
"""Package verified profile kernel, modules and firmware as a signed local APK."""
import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('kernel-build','modules-stage','firmware-root','imagebuilder','sign-key','keys','output'):
  p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--version',required=True);p.add_argument('--epoch',type=int,required=True)
 a=p.parse_args()
 if not re.fullmatch(r'7\.2\.3-r[0-9]+',a.version):raise ValueError('Explicit 7.2.3 package revision required')
 k=a.kernel_build.resolve(strict=True);m=a.modules_stage.resolve(strict=True)
 kp=json.loads((k/'build-status.json').read_text());mp=json.loads((m/'modules-report.json').read_text())
 if kp['stage']!='kernel-complete' or not mp['passed']:raise ValueError('Build stages not complete')
 if kp['profile']!=mp['profile'] or kp['image_sha256']!=mp['kernel_image_sha256']:raise ValueError('Module/kernel provenance mismatch')
 for rel,field in [('arch/arm64/boot/Image','image_sha256'),('.config','config_sha256')]:
  if sha(k/rel)!=kp[field] or kp[field]!=mp.get(field,mp.get('kernel_'+field)):raise ValueError('Kernel changed: '+rel)
 for rel,entry in mp['modules'].items():
  if sha(m/'root'/rel)!=entry['sha256']:raise ValueError('Module changed: '+rel)
 if {str(x.relative_to(m/'root')) for x in (m/'root').rglob('*.ko')}!=set(mp['modules']):raise ValueError('Module inventory changed')
 profile=kp['profile'];groups={'base'}|set(profile.split('-')[1:]);board=ROOT/'boards/t95h'
 config=dict(re.findall(r'^(CONFIG_\w+)=(.*)$',(k/'.config').read_text(),re.M))
 providers={n:o for n,o in json.loads((board/'kernel/package-providers.json').read_text())['config'].items() if config.get('CONFIG_'+o) in ('y','m')}
 ib=a.imagebuilder.resolve(strict=True);apk=ib/'staging_dir/host/bin/apk'
 a.sign_key.resolve(strict=True);a.keys.resolve(strict=True)
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);root=out/'root';shutil.copytree(m/'root',root,symlinks=True)
 # The tested WLAN worker loads this exact path directly with insmod.
 regulators=list((root/'lib/modules').rglob('t95h_aldo2.ko'))
 if len(regulators)!=1:raise ValueError('Regulator module missing or duplicated')
 target=root/'lib/modules'/mp['kernel_release']/'t95h_aldo2.ko'
 if regulators[0]!=target:shutil.move(regulators[0],target)
 # Preserve the tested late-only ANA loading path, outside modalias autoload.
 if 'B' in groups:
  paths=list(root.rglob('t95h_ana_provider.ko'))
  if len(paths)!=1:raise ValueError('ANA module missing or duplicated')
  dst=root/'usr/lib/t95h-gpu';dst.mkdir(parents=True);shutil.move(paths[0],dst/'t95h_ana_provider.ko')
  (dst/'SHA256SUMS').write_text(sha(dst/'t95h_ana_provider.ko')+'  t95h_ana_provider.ko\n')
 subprocess.run(['depmod','-b',str(root),mp['kernel_release']],check=True)
 startup=json.loads((m/'startup/verification.json').read_text())
 if startup['profile']!=profile or sha(m/'startup/t95h.dtb')!=startup['dtb_sha256']:raise ValueError('Profile DT changed')
 (root/'boot').mkdir();shutil.copyfile(k/'arch/arm64/boot/Image',root/'boot/Image');shutil.copyfile(m/'startup/t95h.dtb',root/'boot/t95h.dtb')
 firmware={}
 for entry in json.loads((board/'profiles/integration-draft.json').read_text())['firmware']:
  rel=entry['file']
  # wireless-regdb owns these files; they are also embedded in the kernel.
  if entry['profile'] not in groups or rel.startswith('lib/firmware/regulatory.db'):continue
  source=a.firmware_root.resolve(strict=True)/rel
  if sha(source)!=entry['sha256']:raise ValueError('Firmware source mismatch: '+rel)
  dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
  if sha(dest)!=entry['sha256']:raise ValueError('Firmware copy mismatch: '+rel)
  firmware[rel]=entry['sha256']
 metadata=root/'usr/share/t95h';metadata.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(k/'.config',metadata/'kernel.config')
 (metadata/'kernel-providers.json').write_text(json.dumps({'release':mp['kernel_release'],'config':providers},indent=2)+'\n')
 (metadata/'build-profile.json').write_text(json.dumps({'profile':profile,'kernel':mp['kernel_release'],'kernel_sha256':kp['image_sha256'],'config_sha256':kp['config_sha256'],'dtb_sha256':startup['dtb_sha256'],'modules_sha256':{str(f.relative_to(root)):sha(f) for f in root.rglob('*.ko')},'wlan_firmware':'.58','hardware_validation':'pending'},indent=2)+'\n')
 for path in sorted(root.rglob('*')):
  if path.is_symlink():raise ValueError('Unexpected payload symlink: '+str(path))
  path.chmod(0o755 if path.is_dir() else 0o644);os.utime(path,(a.epoch,a.epoch))
 ib=a.imagebuilder.resolve(strict=True);apk=ib/'staging_dir/host/bin/apk'
 env=dict(os.environ,STAGING_DIR_HOST=str(ib/'staging_dir/host'),SOURCE_DATE_EPOCH=str(a.epoch),TZ='UTC',LC_ALL='C')
 package=out/('t95h-kernel-'+a.version+'.apk')
 provides=' '.join(['kernel='+a.version]+['kmod-'+n+'='+a.version for n in sorted(providers)])
 with (out/'package.log').open('w') as log:
  subprocess.run([str(ib/'staging_dir/host/bin/fakeroot'),str(apk),'mkpkg','--sign-key',str(a.sign_key.resolve(strict=True)),'--files',str(root),'--output',str(package),'--info','name:t95h-kernel','--info','version:'+a.version,'--info','arch:aarch64_cortex-a53','--info','description:T95H '+profile+' kernel and matching modules','--info','license:GPL-2.0-only','--info','provides:'+provides],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run([str(apk),'--keys-dir',str(a.keys.resolve(strict=True)),'verify',str(package)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 report={'profile':profile,'package':package.name,'sha256':sha(package),'version':a.version,'kernel_sha256':kp['image_sha256'],'config_sha256':kp['config_sha256'],'providers':providers,'firmware':firmware,'signed_package_verified':True,'image_ready':False}
 (out/'package-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
