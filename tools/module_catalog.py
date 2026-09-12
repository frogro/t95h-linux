"""Package only catalog entries proven against the actual T95H kernel outputs."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from module_feed import sha, validate_url

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'boards/t95h/kernel/module-catalog.json'

def load():
    data=json.loads(CATALOG.read_text())
    if data['format']!='T95H-KMOD-CATALOG-1' or len(data['packages'])!=976:
        raise ValueError('Unexpected catalog reference')
    for folder,field in [('catalog','config_sha256'),('kconfig-draft','baseline_config_sha256')]:
        if sha(ROOT/f'boards/t95h/profiles/{folder}/base-A-B.config')!=data[field]:
            raise ValueError('Catalog configuration changed without renewed audit')
    return data

def plan(catalog, config, modules, builtins, dependencies):
    """Return package ownership/dependencies and explicit exclusions, never guesses."""
    rows={r['package']:dict(r) for r in catalog['packages']}
    aliases={p.split('=')[0]:r['package'] for r in rows.values() for p in r.get('provides',[])}
    valid={}
    for name,row in rows.items():
        if row['state']!='config_candidate':continue
        bad=[s for s,v in row['symbols'].items() if (v in ('y','m') and config.get('CONFIG_'+s) not in ('y','m')) or (v=='n' and config.get('CONFIG_'+s) in ('y','m'))]
        missing=set(row['objects'])-modules-builtins
        if bad or missing:
            row.update(state='built_payload_or_config_missing',missing_objects=sorted(missing),missing_symbols=bad);continue
        deps=[];unsupported=[]
        for dep in row['depends']:
            if dep.startswith('kernel='):continue
            raw=re.match(r'[\w.+-]+',dep).group()
            depname=aliases.get(raw,raw)
            if not depname.startswith('kmod-'):unsupported.append(dep)
            else:deps.append(depname)
        if unsupported:
            row.update(state='additional_firmware_package_required',unresolved=unsupported);continue
        row['package_dependencies']=sorted(set(deps)-{name});valid[name]=row
    while True:
        removed=[]
        for name,row in valid.items():
            unavailable=set(row['package_dependencies'])-valid.keys()
            if unavailable:row.update(state='catalog_dependency_unavailable',unresolved=sorted(unavailable));removed.append(name)
        if not removed:break
        for name in removed:del valid[name]
    represented={m for row in valid.values() for m in row['objects']} & modules
    missing_retained=set(catalog['retain_objects'])-modules
    if missing_retained:raise ValueError('Baseline modules lost: '+repr(sorted(missing_retained)))
    keep_packages=set(catalog.get('retain_packages',[])) & valid.keys()
    while True:
        expanded=keep_packages|{d for n in keep_packages for d in valid[n]['package_dependencies']}
        if expanded==keep_packages:break
        keep_packages=expanded
    retained=(modules-represented)|set(catalog['retain_objects'])|{m for n in keep_packages for m in valid[n]['objects'] if m in modules}
    while True:
        expanded=retained|{d for m in retained for d in dependencies.get(m,[])}
        if expanded==retained:break
        retained=expanded
    movable=modules-retained
    owner={m:min(n for n,r in valid.items() if m in r['objects']) for m in movable}
    for name,row in valid.items():
        row['owned_objects']=sorted(m for m,n in owner.items() if n==name)
        needs={owner[m] for m in row['objects'] if m in owner}
        needs|={owner[d] for m in row['owned_objects'] for d in dependencies.get(m,[]) if d in owner}
        row['package_dependencies']=sorted((set(row['package_dependencies'])|needs)-{name})
        row['state']='feed_package' if row['owned_objects'] else 'bundled_or_dependency_metapackage'
    # Keep even empty metapackages in the feed, with exact dependencies. They are
    # never represented as owning files already owned by t95h-kernel.
    bundled={n for n,r in valid.items() if not r['owned_objects']}
    while True:
        smaller={n for n in bundled if set(valid[n]['package_dependencies'])<=bundled}
        if smaller==bundled:break
        bundled=smaller
    return {'bundled_packages':sorted(bundled),'packages':valid,'audit':list(rows.values()),'retained_objects':sorted(retained),'movable_objects':sorted(movable)}

def split(root, release, output, providers, version, abi, url, apk, fakeroot, key, keys, epoch, env, kernel):
    catalog=load();validate_url(url);output.mkdir(exist_ok=False)
    config=dict(re.findall(r'^(CONFIG_\w+)=(.*)$',(kernel/'.config').read_text(),re.M))
    folder=root/'lib/modules'/release
    modules={p.name for p in folder.glob('*.ko')}
    builtins={Path(s).name for s in (kernel/'modules.builtin').read_text().splitlines()}
    dependencies={s.split(':')[0]:s.split(':')[1].split() for s in (folder/'modules.dep').read_text().splitlines()}
    selected=plan(catalog,config,modules,builtins,dependencies)
    if not selected['movable_objects']:raise ValueError('Catalog produced no downloadable modules')
    # All original base-contract names must remain either bundled or supported.
    files={}
    for name,row in sorted(selected['packages'].items()):
        stage=output/(name+'.root');stage.mkdir()
        payload={}
        for module in row['owned_objects']:
            rel='lib/modules/'+release+'/'+module;dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.move(folder/module,dst);payload[rel]=sha(dst)
        for path in [stage,*stage.rglob('*')]:
            path.chmod(0o755 if path.is_dir() else 0o644)
            import os
            os.utime(path,(epoch,epoch))
        deps=['t95h-kernel='+version,'t95h-kernel-abi='+abi]+[n+'='+version for n in row['package_dependencies']]
        package=output/(name+'-'+version+'.apk')
        command=[str(fakeroot),str(apk),'mkpkg','--sign-key',str(key),'--files',str(stage),'--output',str(package),'--info','name:'+name,'--info','version:'+version,'--info','arch:aarch64_cortex-a53','--info','description:T95H '+row['title'],'--info','license:GPL-2.0-only','--info','depends:'+' '.join(deps)]
        aliases=[n for n in row.get('provides',[]) if re.fullmatch(r'kmod-[\w.+-]+',n)]
        if aliases:command+=['--info','provides:'+' '.join(n+'='+version for n in aliases)]
        subprocess.run(command,env=env,check=True,stdout=subprocess.DEVNULL)
        files[package.name]={'name':name,'sha256':sha(package),'modules':payload,'dependencies':row['package_dependencies']}
        if name in selected['bundled_packages']:
            providers[name.removeprefix('kmod-')]=next((s for s,v in row['symbols'].items() if v in ('y','m')), 'MODULES')
        else:
            providers.pop(name.removeprefix('kmod-'),None)
    subprocess.run(['depmod','-b',str(root),release],check=True)
    subprocess.run([str(apk),'--keys-dir',str(keys),'mkndx','--sign-key',str(key),'--output',str(output/'packages.adb'),'--pkgname-spec','${name}-${version}.apk',*[str(output/n) for n in files]],env=env,check=True)
    subprocess.run([str(apk),'--keys-dir',str(keys),'verify',str(output/'packages.adb')],env=env,check=True)
    path=root/'etc/apk/repositories.d/99-t95h-module-test.list';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(url+'/packages.adb\n')
    public=root/'etc/apk/keys/t95h-build.pem';public.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(keys/'t95h-build.pem',public)
    proof={'format':'T95H-MODULE-FEED-TEST-1','mode':'catalog','url':url,'abi':abi,'kernel_package_version':version,'packages':files,'index_sha256':sha(output/'packages.adb'),'public_key_sha256':sha(public),'runtime_load_tested':False,'reference_packages':len(catalog['packages']),'catalog_sha256':sha(CATALOG)}
    (output/'module-feed.json').write_text(json.dumps(proof,indent=2)+'\n')
    (output/'catalog-audit.json').write_text(json.dumps(selected,indent=2)+'\n')
    print('Catalog packages:',len(files),'downloadable module objects:',len(selected['movable_objects']),flush=True)
    return proof
