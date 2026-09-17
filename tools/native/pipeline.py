#!/usr/bin/env python3
"""Native OpenWrt CI: resolve once, apply the audited port, build and publish."""
import argparse, ast, hashlib, json, os, re, shutil, subprocess, urllib.request, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import t95h_di300 as di300
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
def build_fingerprint(root, commit, profile, public_key_hash):
    # Version this contract when runner dependencies or build semantics change.
    h=hashlib.sha256(json.dumps([commit, profile, public_key_hash,
        'ubuntu-24.04-x86_64-native-v2'], separators=(',', ':')).encode())
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if not path.is_file() or 'tests' in relative.parts or '__pycache__' in relative.parts:
            continue
        if relative.as_posix() in ('pipeline.py', 'publisher.py'):
            continue
        h.update(relative.as_posix().encode());h.update(path.read_bytes())
    shared=root.parents[1]/'boards/t95h/audio'
    if shared.is_dir():
        for path in sorted(shared.iterdir()):
            if path.is_file():h.update(path.name.encode());h.update(path.read_bytes())
    for path in [root.parent/'t95h_di300.py', *sorted((root.parent/'experimental/di300').glob('*.patch')), root.parent/'experimental/di300/manifest.json']:
        if path.is_file():h.update(path.name.encode());h.update(path.read_bytes())
    # Packaging checks and publishing do not change compiled outputs. Hash the
    # actual preparation/build functions, ignoring comments and formatting.
    tree=ast.parse((root/'pipeline.py').read_text())
    names={'run', 'output', 'sha', 'lock', 'prepare', 'build'}
    functions={node.name:node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for name in sorted(names):
        h.update(ast.dump(functions[name], include_attributes=False).encode())
    return h.hexdigest()

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
    fingerprint = build_fingerprint(HERE, commit, profile, sha(WORK/'public-key.pem'))
    d = dict(version=version,tag=tag,commit=commit,profile=profile,build_commit=os.environ.get('GITHUB_SHA'),fingerprint=fingerprint,feed_id=fingerprint[:16])
    (WORK/'lock.json').write_text(json.dumps(d,indent=2)+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:
            f.write(f'cache_prefix=native-v2-{fingerprint}-{profile}-\nfeed_id={d["feed_id"]}\n')
    print(json.dumps(d))
def prepare(key):
    d=lock();(WORK/'logs').mkdir(exist_ok=True)
    if SOURCE.exists(): raise RuntimeError('Prepare requires an isolated fresh source checkout')
    run('git','clone','--depth','1','--branch',d['tag'],'https://git.openwrt.org/openwrt/openwrt.git',SOURCE)
    if output('git','rev-parse','HEAD',cwd=SOURCE)!=d['commit']: raise RuntimeError('Tag changed after resolution')
    run('git','apply','--check',HERE/'port.patch',cwd=SOURCE)
    run('git','apply',HERE/'port.patch',cwd=SOURCE)
    shutil.copytree(HERE/'overlay',SOURCE,dirs_exist_ok=True)
    for n,(path,digest) in enumerate(di300.patches('6.12'),start=500):
        shutil.copyfile(path,SOURCE/'target/linux/sunxi/patches-6.12'/f'{n}-t95h-di300.patch')
    shutil.copyfile(HERE.parent/'t95h_di300.py',SOURCE/'target/linux/sunxi/image/t95h/t95h_di300.py')
    audio=HERE.parents[1]/'boards/t95h/audio'
    board_files=SOURCE/'package/utils/t95h-board/files'
    shutil.copy2(audio/'t95h-audio-init',board_files/'usr/sbin/t95h-audio-init')
    shutil.copy2(audio/'t95h-audio.conf',board_files/'etc/t95h-audio.conf')
    target=(SOURCE/'target/linux/sunxi/Makefile').read_text()
    if not re.search(r'^KERNEL_PATCHVER\s*:?=\s*6\.12(?:\s|$)',target,re.M): raise RuntimeError('Stable target no longer uses reviewed kernel 6.12; port review required')
    run('./scripts/feeds','update','-a',cwd=SOURCE)
    for line in (SOURCE/'feeds.conf.default').read_text().splitlines():
        if line.startswith('src-git '):
            _,name,url=line.split();pin=url.rsplit('^',1)[-1]
            if not re.fullmatch('[0-9a-f]{40}',pin) or output('git','rev-parse','HEAD',cwd=SOURCE/'feeds'/name)!=pin:
                raise RuntimeError('Unpinned or mismatching stable feed: '+name)
    # Apply reviewed feed fixes only after verifying the upstream pinned commits.
    # These patches are included in resolve()'s compatibility fingerprint.
    for patch in sorted((HERE/'feed-patches').glob('*/*.patch')):
        feed=SOURCE/'feeds'/patch.parent.name
        run('git','apply','--check',patch,cwd=feed)
        run('git','apply',patch,cwd=feed)
    run('./scripts/feeds','install','-a',cwd=SOURCE)
    groups=json.loads((HERE/'packages.json').read_text());selected=set()
    if 'A' in d['profile'].split('-'):selected.update(groups['A'])
    if 'B' in d['profile'].split('-'):selected.update(groups['B'])
    config_only=set(groups.get('B_config_only', []))
    config_selected=selected | (config_only if 'B' in d['profile'].split('-') else set())
    optional=set(groups['A'])|set(groups['B'])|config_only;lines=[]
    for line in (HERE/'native-common.config').read_text().splitlines():
        if any(line.startswith('CONFIG_PACKAGE_'+p+'=') or line=='# CONFIG_PACKAGE_'+p+' is not set' for p in optional):continue
        lines.append(line)
    for p in sorted(optional):
        lines.append('CONFIG_PACKAGE_'+p+'='+('y' if p in config_selected else 'm') if p in config_selected or p.startswith('kmod-') else '# CONFIG_PACKAGE_'+p+' is not set')
    lines += ['CONFIG_VERSIONOPT=y',f'CONFIG_VERSION_NUMBER="{d["version"]}"',f'CONFIG_VERSION_REPO="https://downloads.openwrt.org/releases/{d["version"]}"']
    (SOURCE/'.config').write_text('\n'.join(lines)+'\n')
    shutil.copy2(key,SOURCE/'private-key.pem');(SOURCE/'private-key.pem').chmod(0o600)
    shutil.copy2(WORK/'public-key.pem',SOURCE/'public-key.pem')
    keys=SOURCE/'package/utils/t95h-board/files/etc/apk/keys';keys.mkdir(parents=True,exist_ok=True)
    shutil.copy2(WORK/'public-key.pem',keys/'t95h-native.pem')
    (SOURCE/'package/utils/t95h-board/files/usr/share/t95h/profile').write_text(d['profile']+'\n')
    run('make','defconfig',cwd=SOURCE)
    config=(SOURCE/'.config').read_text()
    for p in config_selected|set(groups['required_base_packages']):
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
def check_image_packages(expected, manifest):
    installed={line.split()[0] for line in manifest.splitlines() if line.strip()}
    missing=sorted(set(expected)-installed)
    if missing:
        raise RuntimeError('Incomplete image package selection: '+', '.join(missing))

def package():
    d=lock();out=WORK/'release';out.mkdir(exist_ok=True);src=SOURCE/'bin/targets/sunxi/cortexa53'
    manifests=list(src.glob('*t95h_tvbox.manifest'))
    if len(manifests)!=1:raise RuntimeError('Package manifest missing/ambiguous')
    check_image_packages(json.loads((WORK/'selected.json').read_text()), manifests[0].read_text())
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
    # Installer contains the same rootfs and a verified eMMC payload for this profile.
    pair=WORK/'installer-inputs';pair.mkdir(exist_ok=True)
    stem=f'T95H-OpenWrt-{d["version"]}-kernel6-{d["profile"]}'
    for medium in ['sdcard','emmc']:
        image=pair/f'{stem}-{medium}-install.img.gz'
        shutil.copy2(out/image.name,image)
        run(SOURCE/'staging_dir/host/bin/fwtool','-t','-i',pair/f'{medium}.json',image)
    compiler=next((SOURCE/'staging_dir').glob('toolchain-*/bin/aarch64-openwrt-linux-musl-gcc'))
    installer=WORK/'installer-sd'
    if installer.exists():shutil.rmtree(installer)
    run('python3',HERE.parents[1]/'tools/build-media-installer.py',
        '--sd',pair/f'{stem}-sdcard-install.img.gz','--emmc',pair/f'{stem}-emmc-install.img.gz',
        '--os','openwrt6','--compiler',compiler,'--output',installer)
    report=json.loads((installer/'installer.json').read_text())
    shutil.copy2(installer/report['file'],out/report['file'])
    shutil.copy2(installer/'installer.json',out/'installer.json')
    shutil.copy2(SOURCE/'target/linux/sunxi/base-files/lib/upgrade/platform.sh',out/'platform-dual-update.sh')
    bridge=(HERE/'migrate-upgrade.sh').read_text().replace('@PLATFORM_SHA256@',sha(out/'platform-dual-update.sh'))
    (out/'migrate-upgrade.sh').write_text(bridge)
    (out/'migrate-upgrade.sh').chmod(0o755)
    shutil.copy2(WORK/'lock.json',out/'build-lock.json')
    shutil.copy2(WORK/'logs/native-module-audit.json',out/'hardware-modules.json')
    (out/'RELEASE-NOTES.md').write_text(f'''T95H OpenWrt {d['version']} – Kernel 6 – {d['profile']}

SD und eMMC haben jeweils ein Installations- und ein Sysupgrade-Image. Die beiden Dateien pro Medium sind inhaltsgleich; die Namen kennzeichnen den Verwendungszweck. Für LuCI das zum laufenden Medium passende sysupgrade.img.gz wählen und Einstellungen beibehalten aktivieren. Keine Prüfung mit Force umgehen. Bestehende Kernel-6-Images benötigen einmalig den geprüften Übergang: migrate-upgrade.sh und platform-dual-update.sh aus demselben Release herunterladen, SHA256SUMS prüfen, `sh migrate-upgrade.sh --check`, dann `sh migrate-upgrade.sh --apply`. Unbekannte Altstände werden abgewiesen. Danach übernimmt Sysupgrade auch den korrigierten SPL mit Rückleseprüfung; MBR, spätere Firmware, Einstellungen und eine vorhandene dritte Installer-Partition bleiben erhalten.

Zusätzlich: kombiniertes sd-emmc-installer.img.gz mit exakt demselben Profil. Nur zur Erstinstallation auf SD verwenden, niemals als Sysupgrade-Eingabe. Zum Aktualisieren einer solchen SD das normale sdcard-sysupgrade.img.gz verwenden. Zum eMMC-Installieren die dritte Partition einhängen und install-emmc.sh dort ausdrücklich starten; eMMC wird dabei vollständig gelöscht und die OpenWrt-Konfiguration übernommen.

WLAN-Vorgabe: OpenWrt / openwrtopenwrt. Beim Update wird nur der historische AP-Name T95H-Test migriert; individuell gewählte SSIDs bleiben erhalten.

SD- und eMMC-Updates einschließlich Konfigurationsübernahme wurden mit dem lokalen Vorgänger praktisch getestet. Der frische CI-Build ist noch nicht auf Hardware geprüft. Unzuverlässige Kaltstarts (mehrere Einschaltversuche) sowie XR819-Interruptmeldungen bleiben offen.

Enthalten: getesteter SD-SPL, daraus abgeleiteter noch hardwareungetesteter eMMC-SPL, bisheriger HDMI-Stand, GPU/CPU-Regelung, vollständiger verfügbarer OpenWrt-Modulkatalog und signierter versionsgebundener Feed. Die schnelle procd-Prüfung verhindert einen Watchdog-Neustart; die vollständige Dekompressionsprüfung bleibt vor jedem Schreibzugriff zwingend.

Alte Systeme benötigen vor dem ersten Update den passenden Plattformskriptstand. Der kombinierte Installer enthält den im Repository gepflegten Installationshelfer.
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
