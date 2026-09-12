"""Isolated release feed experiment: two leaf modules, exact kernel ABI binding."""
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading

SELECTED = {'veth': 'veth.ko', 'sched-cake': 'sch_cake.ko'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate_url(url):
    if not re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+/releases/download/t95h-feedtest-\d+-\d+', url):
        raise ValueError('Expected immutable GitHub feed-test release URL')
    return url

def split(root, release, output, providers, version, abi, url, apk, fakeroot, key, keys, epoch, env):
    validate_url(url)
    root, output = Path(root), Path(output)
    output.mkdir(exist_ok=False)
    folder = root/'lib/modules'/release
    # Only split leaf modules. No retained module may depend on a removed object.
    removed = set(SELECTED.values())
    for line in (folder/'modules.dep').read_text().splitlines():
        name, deps = line.split(':', 1)
        if name not in removed and set(deps.split()) & removed:
            raise ValueError('Selected feed module is not a leaf: ' + name)
    files = {}
    for name, module in SELECTED.items():
        if name not in providers or not (folder/module).is_file():
            raise ValueError('Missing selected module/provider: ' + name)
        package_name = 'kmod-' + name
        stage = output/(package_name + '.root')
        destination = stage/'lib/modules'/release/module
        destination.parent.mkdir(parents=True)
        shutil.move(folder/module, destination)
        for path in stage.rglob('*'):
            path.chmod(0o755 if path.is_dir() else 0o644)
            os.utime(path, (epoch, epoch))
        package = output/(package_name+'-'+version+'.apk')
        subprocess.run([str(fakeroot), str(apk), 'mkpkg', '--sign-key', str(key),
            '--files', str(stage), '--output', str(package),
            '--info', 'name:'+package_name, '--info', 'version:'+version,
            '--info', 'arch:aarch64_cortex-a53', '--info', 'license:GPL-2.0-only',
            '--info', 'description:T95H isolated module-feed test '+name,
            '--info', 'depends:t95h-kernel='+version+' t95h-kernel-abi='+abi],
            env=env, check=True)
        subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(package)],env=env,check=True)
        files[package.name]={'sha256':sha(package),'name':package_name,
            'module':'lib/modules/'+release+'/'+module,'module_sha256':sha(destination)}
        del providers[name]
    subprocess.run(['depmod','-b',str(root),release],check=True)
    subprocess.run([str(apk),'--keys-dir',str(keys),'mkndx','--sign-key',str(key),'--output',str(output/'packages.adb'),
        '--pkgname-spec','${name}-${version}.apk',*[str(output/name) for name in files]],env=env,check=True)
    subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(output/'packages.adb')],env=env,check=True)
    config = root/'etc/apk/repositories.d/99-t95h-module-test.list'
    config.parent.mkdir(parents=True,exist_ok=True)
    config.write_text(url+'/packages.adb\n')
    public_key=root/'etc/apk/keys/t95h-build.pem'
    public_key.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(Path(keys)/'t95h-build.pem',public_key)
    proof={'format':'T95H-MODULE-FEED-TEST-1','url':url,'abi':abi,'kernel_package_version':version,
           'packages':files,'index_sha256':sha(output/'packages.adb'),
           'public_key_sha256':sha(public_key),'runtime_load_tested':False}
    (output/'module-feed.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass

def exercise(feed, kernel, apk, fakeroot, key, keys, env):
    """Actual HTTP APK install/removal and wrong-ABI rejection, no host mutation."""
    feed, kernel = Path(feed).resolve(), Path(kernel).resolve()
    proof=json.loads((feed/'module-feed.json').read_text())
    handler=functools.partial(QuietHandler,directory=str(feed))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix='t95h-feed-test-') as temp:
            temp=Path(temp); repository=temp/'repositories'
            untrusted=temp/'untrusted-keys';untrusted.mkdir()
            signature=subprocess.run([str(apk),'--keys-dir',str(untrusted),'verify',str(feed/'packages.adb')],
                env=env,capture_output=True,text=True)
            if signature.returncode==0 or 'UNTRUSTED' not in signature.stdout+signature.stderr:
                raise ValueError('Index without trusted key was not rejected as untrusted')
            repository.write_text('http://127.0.0.1:'+str(server.server_port)+'/packages.adb\n')
            names=[p['name'] for p in proof['packages'].values()]
            def cmd(root,*args,success=True):
                result=subprocess.run([str(apk),'--root',str(root),'--arch','aarch64_cortex-a53',
                    '--keys-dir',str(keys),'--repositories-file',str(repository),'--no-cache',
                    '--no-scripts',*(['--usermode'] if args[0]=='add' else []),*args],env=env,capture_output=True,text=True)
                if (result.returncode==0)!=success:
                    raise ValueError('APK feed test unexpected result: '+result.stdout+result.stderr)
                return result
            root=temp/'positive';root.mkdir()
            cmd(root,'add','--initdb','--force-non-repository',str(kernel))
            for item in proof['packages'].values():
                if (root/item['module']).exists():raise ValueError('Feed payload already in test image')
            cmd(root,'add',*names)
            for item in proof['packages'].values():
                if sha(root/item['module'])!=item['module_sha256']:raise ValueError('Downloaded payload differs')
            # Removal must not remove or change the kernel image.
            kernel_hash=sha(root/'boot/Image')
            cmd(root,'del',*names)
            if sha(root/'boot/Image')!=kernel_hash:raise ValueError('Module removal changed kernel')
            if any((root/i['module']).exists() for i in proof['packages'].values()):raise ValueError('Module removal failed')
            stage=temp/'wrong-root';stage.mkdir();wrong=temp/'wrong-kernel.apk'
            subprocess.run([str(fakeroot),str(apk),'mkpkg','--sign-key',str(key),
                '--files',str(stage),'--output',str(wrong),'--info','name:t95h-kernel',
                '--info','version:'+proof['kernel_package_version'],'--info','arch:aarch64_cortex-a53',
                '--info','description:wrong ABI fixture','--info','license:GPL-2.0-only',
                '--info','provides:t95h-kernel-abi=0~deadbeef'],env=env,check=True,capture_output=True)
            negative=temp/'negative';negative.mkdir()
            cmd(negative,'add','--initdb','--force-non-repository',str(wrong))
            rejected=cmd(negative,'add',*names,success=False)
            if 't95h-kernel-abi' not in rejected.stdout+rejected.stderr:
                raise ValueError('Failure did not identify ABI dependency')
            if any((negative/i['module']).exists() for i in proof['packages'].values()):raise ValueError('Wrong ABI installed payload')
            proof['apk_http_install_remove_verified']=True
            proof['wrong_kernel_abi_rejected']=True
            proof['untrusted_index_rejected']=True
            (feed/'module-feed.json').write_text(json.dumps(proof,indent=2)+'\n')
            return proof
    finally:
        server.shutdown();server.server_close();thread.join()
