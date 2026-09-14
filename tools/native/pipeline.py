#!/usr/bin/env python3
"""Native OpenWrt CI: resolve once, apply the audited port, build and publish."""
import argparse, hashlib, json, os, re, shutil, subprocess, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get('NATIVE_WORK', 'build/native')).resolve()
SOURCE = WORK / 'source'
PROFILES = ('base', 'base-A', 'base-B', 'base-A-B')
def run(*args, cwd=None, **kw):
    return subprocess.run([str(x) for x in args], cwd=cwd, check=True, **kw)
def output(*args, cwd=None):
    return subprocess.check_output([str(x) for x in args], cwd=cwd, text=True).strip()
def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def lock(): return json.loads((WORK/'lock.json').read_text())
def resolve(profile, key):
    WORK.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen('https://downloads.openwrt.org/.versions.json', timeout=60) as f:
        version = json.load(f)['stable_version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version): raise RuntimeError('Not a final stable release')
    tag = 'v'+version
    refs = output('git','ls-remote','https://git.openwrt.org/openwrt/openwrt.git',f'refs/tags/{tag}',f'refs/tags/{tag}^{{}}').splitlines()
    refs = dict(line.split()[::-1] for line in refs)
    commit = refs.get(f'refs/tags/{tag}^{{}}', refs.get(f'refs/tags/{tag}'))
    if not commit: raise RuntimeError('Stable tag missing')
    run('openssl','pkey','-in',key,'-pubout','-out',WORK/'public-key.pem')
    h = hashlib.sha256((commit+profile+'ubuntu-24.04-x86_64-native-v1'+sha(WORK/'public-key.pem')).encode())
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            h.update(str(p.relative_to(HERE)).encode());h.update(p.read_bytes())
    fingerprint = h.hexdigest()
    d = dict(version=version,tag=tag,commit=commit,profile=profile,build_commit=os.environ.get('GITHUB_SHA'),fingerprint=fingerprint,feed_id=fingerprint[:16])
    (WORK/'lock.json').write_text(json.dumps(d,indent=2)+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:
            f.write(f'cache_key=native-v1-{fingerprint}-{profile}\nfeed_id={d["feed_id"]}\n')
    print(json.dumps(d))
def prepare(key):
    d=lock();(WORK/'logs').mkdir(exist_ok=True)
    if SOURCE.exists(): raise RuntimeError('Prepare requires an isolated fresh source checkout')
    run('git','clone','--depth','1','--branch',d['tag'],'https://git.openwrt.org/openwrt/openwrt.git',SOURCE)
    if output('git','rev-parse','HEAD',cwd=SOURCE)!=d['commit']: raise RuntimeError('Tag changed after resolution')
    run('git','apply','--check',HERE/'port.patch',cwd=SOURCE)
    run('git','apply',HERE/'port.patch',cwd=SOURCE)
    shutil.copytree(HERE/'overlay',SOURCE,dirs_exist_ok=True)
    target=(SOURCE/'target/linux/sunxi/Makefile').read_text()
    if not re.search(r'^KERNEL_PATCHVER\s*:?=\s*6\.',target,re.M): raise RuntimeError('Stable target no longer uses kernel 6; port review required')
    run('./scripts/feeds','update','-a',cwd=SOURCE)
    for line in (SOURCE/'feeds.conf.default').read_text().splitlines():
        if line.startswith('src-git '):
            _,name,url=line.split();pin=url.rsplit('^',1)[-1]
            if not re.fullmatch('[0-9a-f]{40}',pin) or output('git','rev-parse','HEAD',cwd=SOURCE/'feeds'/name)!=pin:
                raise RuntimeError('Unpinned or mismatching stable feed: '+name)
    run('./scripts/feeds','install','-a',cwd=SOURCE)
    groups=json.loads((HERE/'packages.json').read_text());selected=set()
    if 'A' in d['profile'].split('-'):selected.update(groups['A'])
    if 'B' in d['profile'].split('-'):selected.update(groups['B'])
    optional=set(groups['A'])|set(groups['B']);lines=[]
    for line in (HERE/'native-common.config').read_text().splitlines():
        if any(line.startswith('CONFIG_PACKAGE_'+p+'=') or line=='# CONFIG_PACKAGE_'+p+' is not set' for p in optional):continue
        lines.append(line)
    for p in sorted(optional):
        lines.append('CONFIG_PACKAGE_'+p+'='+('y' if p in selected else 'm') if p in selected or p.startswith('kmod-') else '# CONFIG_PACKAGE_'+p+' is not set')
    lines += ['CONFIG_VERSIONOPT=y',f'CONFIG_VERSION_NUMBER="{d["version"]}"',f'CONFIG_VERSION_REPO="https://downloads.openwrt.org/releases/{d["version"]}"']
    (SOURCE/'.config').write_text('\n'.join(lines)+'\n')
    shutil.copy2(key,SOURCE/'private-key.pem');(SOURCE/'private-key.pem').chmod(0o600)
    shutil.copy2(WORK/'public-key.pem',SOURCE/'public-key.pem')
    keys=SOURCE/'package/utils/t95h-board/files/etc/apk/keys';keys.mkdir(parents=True,exist_ok=True)
    shutil.copy2(WORK/'public-key.pem',keys/'t95h-native.pem')
    (SOURCE/'package/utils/t95h-board/files/usr/share/t95h/profile').write_text(d['profile']+'\n')
    run('make','defconfig',cwd=SOURCE)
    config=(SOURCE/'.config').read_text()
    for p in selected|set(groups['required_base_packages']):
        if 'CONFIG_PACKAGE_'+p+'=y\n' not in config: raise RuntimeError('Required package not enabled: '+p)
    if 'CONFIG_ALL_KMODS=y' not in config: raise RuntimeError('Full module catalog disabled')
    (WORK/'selected.json').write_text(json.dumps(sorted(selected|set(groups['required_base_packages'])),indent=2))
def build(jobs):
    d=lock();os.environ.update(NATIVE_WORK=str(WORK),T95H_FEED_ID=d['feed_id'],LC_ALL='C',TZ='UTC')
    for stage in ['download','tools/install','toolchain/install','target/linux/prepare','target/linux/compile']:
        print('BUILD STAGE:',stage,flush=True)
        run('make',f'-j{jobs}',stage,'V=s',f'T95H_FEED_ID={d["feed_id"]}',cwd=SOURCE)
    run('python3',HERE/'check-native-modules.py')
    run('make',f'-j{jobs}','V=s',f'T95H_FEED_ID={d["feed_id"]}',cwd=SOURCE)
    run('python3',HERE/'kernel-catalog.py','export')
    package()
def package():
    d=lock();out=WORK/'release';out.mkdir(exist_ok=True);src=SOURCE/'bin/targets/sunxi/cortexa53'
    manifests=list(src.glob('*t95h_tvbox.manifest'))
    if len(manifests)!=1:raise RuntimeError('Package manifest missing/ambiguous')
    installed={l.split()[0] for l in manifests[0].read_text().splitlines() if l.strip()}
    if not set(json.loads((WORK/'selected.json').read_text()))<=installed:raise RuntimeError('Incomplete image package selection')
    shutil.copy2(manifests[0],out/'packages.manifest')
    for medium in ['sdcard','emmc']:
        p=src/f'openwrt-sunxi-cortexa53-t95h_tvbox-ext4-{medium}.img.gz'
        if not p.is_file():raise RuntimeError('Missing image: '+str(p))
        # Assembler already checked FAT/ext4, DTB, modules and update handler.
        meta=WORK/f'{medium}-metadata.json'
        run(SOURCE/'staging_dir/host/bin/fwtool','-i',meta,p)
        if 't95h,h616-tvbox' not in json.loads(meta.read_text())['supported_devices']:raise RuntimeError('Wrong device metadata')
        name=f'T95H-OpenWrt-{d["version"]}-kernel6-{d["profile"]}-{medium}'
        for purpose in ['install','sysupgrade']:shutil.copy2(p,out/f'{name}-{purpose}.img.gz')
    shutil.copy2(SOURCE/'target/linux/sunxi/base-files/lib/upgrade/platform.sh',out/'platform-dual-update.sh')
    shutil.copy2(WORK/'lock.json',out/'build-lock.json')
    shutil.copy2(WORK/'logs/native-module-audit.json',out/'hardware-modules.json')
    (out/'RELEASE-NOTES.md').write_text(f'''T95H OpenWrt {d['version']} – Kernel 6 – {d['profile']}

SD und eMMC haben jeweils ein Installations- und ein Sysupgrade-Image. Die beiden Dateien pro Medium sind inhaltsgleich; die Namen kennzeichnen den Verwendungszweck. Für LuCI das zum laufenden Medium passende sysupgrade.img.gz wählen und Einstellungen beibehalten aktivieren. Keine Prüfung mit Force umgehen.

SD- und eMMC-Updates einschließlich Konfigurationsübernahme wurden mit dem lokalen Vorgänger praktisch getestet. Der frische CI-Build ist noch nicht auf Hardware geprüft. Unzuverlässige Kaltstarts (mehrere Einschaltversuche) sowie XR819-Interruptmeldungen bleiben offen.

Enthalten: getesteter Boot-/eMMC-/HDMI-Stand, GPU/CPU-Regelung, vollständiger verfügbarer OpenWrt-Modulkatalog und signierter versionsgebundener Feed. Die schnelle procd-Prüfung verhindert einen Watchdog-Neustart; die vollständige Dekompressionsprüfung bleibt vor jedem Schreibzugriff zwingend.

Alte Systeme benötigen vor dem ersten Update den passenden Plattformskriptstand. Persönliche eMMC-Installationshelfer gehören nicht zu diesem Release.
''')
    sums=[sha(p)+'  '+p.name for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS']
    (out/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
def publish():
    from publisher import GitHub
    d=lock();repo=os.environ['GITHUB_REPOSITORY']
    client=GitHub(repo)
    branch=client.api(f'repos/{repo}')['default_branch']
    commit=client.api(f'repos/{repo}/commits/{branch}')['sha']
    feeds=list((WORK/'releases').glob('native-kmods-*'))
    if len(feeds)!=1:raise RuntimeError('Expected one verified module repository')
    feed=feeds[0]
    client.publish(feed.name, sorted(feed.iterdir()), commit,
        'T95H native kernel module feed '+d['feed_id'],
        'Signed kernel packages for the matching native T95H build. Do not mix kernel ABIs.')
    # Stable across job retries, so an interrupted image upload can resume too.
    tag=f'openwrt-native-{d["version"]}-{d["profile"]}-{os.environ["GITHUB_RUN_ID"]}'
    out=WORK/'release'
    # Preserve the original checksummed notes and assets across retries.
    notes=(out/'RELEASE-NOTES.md').read_text()+f'\nBuild source commit: {d.get("build_commit", os.environ["GITHUB_SHA"])}\n'
    client.publish(tag, [p for p in sorted(out.iterdir()) if p.name!='publication-notes.md'],
        commit, f'T95H OpenWrt {d["version"]} Kernel 6 SD/eMMC ({d["profile"]})', notes, prerelease=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['resolve','prepare','build','publish']);p.add_argument('--profile',choices=PROFILES,default='base');p.add_argument('--key',type=Path);p.add_argument('--jobs',type=int,default=2);a=p.parse_args()
    if a.command=='resolve':resolve(a.profile,a.key)
    elif a.command=='prepare':prepare(a.key)
    elif a.command=='build':build(a.jobs)
    else:publish()
