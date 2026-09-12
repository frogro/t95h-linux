"""Real APK transport/ABI/signature tests with synthetic, non-loadable payloads."""
from pathlib import Path
import sys,tempfile,subprocess,os,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import module_feed
import module_catalog
import argparse
p=argparse.ArgumentParser();p.add_argument('--imagebuilder',type=Path,required=True);ib=p.parse_args().imagebuilder.resolve()
apk=ib/'staging_dir/host/bin/apk';fakeroot=ib/'staging_dir/host/bin/fakeroot'
env=dict(os.environ,STAGING_DIR_HOST=str(ib/'staging_dir/host'))
with tempfile.TemporaryDirectory(prefix='t95h-feed-fixture-') as tmp:
 t=Path(tmp);keys=t/'keys';keys.mkdir();key=t/'private.pem'
 subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(key)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 subprocess.run(['openssl','pkey','-in',str(key),'-pubout','-out',str(keys/'t95h-build.pem')],check=True,stdout=subprocess.DEVNULL)
 root=t/'root';folder=root/'lib/modules/7.2.3-test';folder.mkdir(parents=True)
 # Synthetic packaging fixtures only, never loaded into a kernel.
 for name in ['veth.ko','sch_cake.ko']:(folder/name).write_bytes(b'packaging-fixture-not-a-loadable-module')
 (folder/'modules.dep').write_text('veth.ko:\nsch_cake.ko:\n')
 (root/'boot').mkdir();(root/'boot/Image').write_bytes(b'kernel fixture')
 providers={n:n for n in module_feed.SELECTED}
 # Both synthetic modules have been moved out before depmod runs.
 for name in ['modules.order','modules.builtin','modules.builtin.modinfo']:(folder/name).write_text('')
 kernel_tree=t/'kernel-tree';kernel_tree.mkdir();(kernel_tree/'.config').write_text('CONFIG_TEST=m\n');(kernel_tree/'modules.builtin').write_text('')
 def row(n,objs,deps=[]):return dict(package=n,state='config_candidate',objects=objs,depends=deps,provides=[n+'-any'],symbols={'TEST':'m'},title=n)
 module_catalog.load=lambda: {'retain_objects':[],'packages':[row('kmod-veth',['veth.ko']),row('kmod-sched-cake',['sch_cake.ko'],['kmod-veth-any']),row('kmod-z-alias',['veth.ko'])]}
 module_catalog.split(root,'7.2.3-test',t/'feed',providers,'7.2.3-r99999','0~abc','https://github.com/frogro/t95h-linux/releases/download/t95h-feedtest-1-1',apk,fakeroot,key,keys,1780000000,env,kernel_tree)
 kernel=t/'t95h-kernel.apk'
 subprocess.run([str(fakeroot),str(apk),'mkpkg','--sign-key',str(key),'--files',str(root),'--output',str(kernel),'--info','name:t95h-kernel','--info','version:7.2.3-r99999','--info','arch:aarch64_cortex-a53','--info','description:fixture','--info','license:GPL-2.0-only','--info','provides:t95h-kernel-abi=0~abc'],env=env,check=True)
 print(json.dumps(module_feed.exercise(t/'feed',kernel,apk,fakeroot,key,keys,env),indent=2))
