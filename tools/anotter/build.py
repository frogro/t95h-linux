#!/usr/bin/env python3
"""Build an experimental Debian/Anotter ARM64 SD image; never open block devices."""
import argparse, gzip, hashlib, json, os, re, shutil, struct, subprocess, tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
M = 1048576
DISK = 'a0950001'
REQUIRED = 'DEVTMPFS DEVTMPFS_MOUNT TMPFS TMPFS_POSIX_ACL TMPFS_XATTR CGROUPS MEMCG CGROUP_PIDS CGROUP_FREEZER CGROUP_DEVICE NAMESPACES USER_NS UTS_NS IPC_NS PID_NS NET_NS SECCOMP SECCOMP_FILTER FHANDLE INOTIFY_USER SIGNALFD TIMERFD EPOLL UNIX UNIX_DIAG BINFMT_ELF BINFMT_SCRIPT AUTOFS_FS EXT4_FS VFAT_FS NLS_CODEPAGE_437 NLS_ISO8859_1'.split()

def run(*args, **kw):
    print('+', *map(str, args), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kw)

def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def put(root, name, text, mode=0o644):
    p = root / name; p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_symlink(): p.unlink()
    p.write_text(text); p.chmod(mode)

def config(text):
    values = {}
    for line in text.splitlines():
        m = re.fullmatch(r'(CONFIG_\w+)=(.*)', line)
        if m: values[m[1]] = m[2]
        m = re.fullmatch(r'# (CONFIG_\w+) is not set', line)
        if m: values[m[1]] = 'n'
    values.update({'CONFIG_'+x: 'y' for x in REQUIRED})
    values.update(CONFIG_LOCALVERSION='"-t95h-anotter"', CONFIG_LOCALVERSION_AUTO='n', CONFIG_INITRAMFS_SOURCE='""')
    return '\n'.join(f'# {k} is not set' if v == 'n' else f'{k}={v}' for k,v in sorted(values.items()))+'\n'

def prefix(data):
    if len(data) != 4*M or data[510:512] != b'\x55\xaa': raise ValueError('Invalid boot prefix')
    b = bytearray(data); b[440:444] = struct.pack('<I', int(DISK,16)); b[446:510] = bytes(64)
    for i, start, size, kind in [(0,8192,262144,12),(1,270336,12582912,131)]:
        b[446+i*16:462+i*16] = struct.pack('<B3sB3sII',0,bytes(3),kind,bytes(3),start,size)
    assert b[512:] == data[512:]
    return b

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=2); a=p.parse_args()
    if os.geteuid() != 0: raise SystemExit('Build requires root for isolated ARM64 chroot')
    o=a.output.resolve(); o.mkdir(parents=True,exist_ok=False)
    lock=json.loads((ROOT/'boards/t95h/build-inputs.json').read_text())
    if sha(a.inputs) != lock['sha256']: raise ValueError('Input archive mismatch')
    with tarfile.open(a.inputs) as t: t.extractall(o/'inputs',filter='data')
    inputs=o/'inputs'; tc=inputs/'toolchain'; fw=inputs/'firmware'
    if sha(inputs/'prefix.bin') != lock['boot_prefix_sha256']: raise ValueError('Prefix mismatch')
    upstream=json.loads(subprocess.check_output(['gh','api','repos/Manawyrm/AnotterKiosk/releases/latest'],text=True))
    tag=upstream['tag_name']
    if upstream['prerelease'] or upstream['draft'] or not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+',tag): raise ValueError('No stable Anotter release')
    run('git','clone','--depth','1','--branch',tag,'https://github.com/Manawyrm/AnotterKiosk.git',o/'upstream')
    commit=subprocess.check_output(['git','-C',str(o/'upstream'),'rev-parse','HEAD'],text=True).strip()
    # Refuse a future distro transition until this adapter is reviewed.
    if 'trixie' not in (o/'upstream/build_x86.sh').read_text(): raise ValueError('Upstream Debian suite changed')
    request={'anotter':tag,'anotter_commit':commit,'debian_suite':'trixie','architecture':'arm64','profile':'base-B','hardware_tested':False}
    put(o,'request.json',json.dumps(request,indent=2)+'\n')
    def tool(name,*args): run('/usr/bin/python3',ROOT/'tools'/name,*args)
    tool('download-kernel-archive.py','--output',o/'kernel.tar.xz')
    tool('prepare-kernel-source.py','--archive',o/'kernel.tar.xz','--output',o/'source')
    put(o,'anotter.config',config((ROOT/'boards/t95h/profiles/kconfig-draft/base-B.config').read_text()))
    tool('build-profile-kernel.py','--source-stage',o/'source','--toolchain',tc,'--firmware-root',fw,'--profile','base-B','--config',o/'anotter.config','--output',o/'kernel','--jobs',a.jobs,'--epoch',lock['epoch'])
    tool('build-profile-modules.py','--kernel-build',o/'kernel','--toolchain',tc,'--output',o/'modules','--jobs',a.jobs,'--epoch',lock['epoch'])
    keydir=ROOT/'boards/t95h/anotter/keys'
    expected={'archive-key-13.asc':'04B54C3CDCA79751B16BC6B5225629DF75B188BD','archive-key-13-security.asc':'5E04A1E3223A19A20706E20F9904613D4CCE68C6','release-13.asc':'41587F7DB8C774BCCF131416762F67A0B2C39DE4'}
    keyring=o/'debian-trixie.gpg'
    with keyring.open('wb') as target:
        for name,fingerprint in expected.items():
            data=subprocess.check_output(['gpg','--batch','--show-keys','--with-colons',str(keydir/name)],text=True)
            actual=next(line.split(':')[9] for line in data.splitlines() if line.startswith('fpr:'))
            if actual!=fingerprint: raise ValueError('Debian signing key mismatch')
            target.write(subprocess.check_output(['gpg','--batch','--dearmor'],input=(keydir/name).read_bytes()))
    root=o/'root'
    packages='debian-archive-keyring,systemd-sysv,udev,sudo,locales,dbus-user-session,polkitd,dhcpcd,rsync,ca-certificates,xserver-xorg-core,xserver-xorg-input-libinput,xinit,libgl1-mesa-dri,mesa-utils,alsa-utils,kmod'
    run('mmdebstrap','--keyring='+str(keyring),'--architectures=arm64','--variant=minbase','--include='+packages,'trixie',root,
        'deb https://deb.debian.org/debian trixie main non-free-firmware',
        'deb https://deb.debian.org/debian trixie-updates main non-free-firmware',
        'deb https://security.debian.org/debian-security trixie-security main non-free-firmware')
    # policy-rc.d blocks all service startup on the builder.
    put(root,'usr/sbin/policy-rc.d','#!/bin/sh\nexit 101\n',0o755)
    shutil.copytree(o/'upstream/kiosk_skeleton',root/'kiosk_skeleton',symlinks=True)
    put(root,'etc/fstab',f'PARTUUID={DISK}-02 / ext4 ro,noatime 0 1\nPARTUUID={DISK}-01 /boot/firmware vfat ro,umask=0077 0 2\n')
    mounts=[]
    try:
        for typ,dest in [('proc','proc'),('sysfs','sys'),('devtmpfs','dev')]:
            run('mount','-t',typ,typ,root/dest); mounts.append(root/dest)
        run('chroot',root,'useradd','-U','-m','-s','/bin/bash','-u','1000','-G','audio,video,users,input,adm,dialout,plugdev,render','pi')
        run('chroot',root,'/bin/bash','/kiosk_skeleton/build.sh')
        run('chroot',root,'/bin/sh','-c',"echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen; locale-gen")
        # No shared password or host key in public images. FAT authorized_keys supplies access.
        run('chroot',root,'usermod','-p','*','root')
        for unit in ['kiosk-watchdog','kiosk-wifi']:
            run('chroot',root,'systemctl','disable',unit)
        run('chroot',root,'dpkg-query','-W','-f=${Package}\t${Version}\t${Architecture}\n',stdout=(o/'packages.tsv').open('w'))
        run('chroot',root,'apt-get','clean')
    finally:
        for path in reversed(mounts): run('umount',path)
    shutil.rmtree(root/'kiosk_skeleton')
    # Normal systemd boot, no Raspberry Pi firmware/init or Xorg configuration.
    for name in ['20-noglamor.conf']:
        (root/'usr/share/X11/xorg.conf.d'/name).unlink(missing_ok=True)
    (root/'etc/X11/xorg.conf.d/99-v3d.conf').unlink(missing_ok=True)
    put(root,'etc/network/interfaces','auto lo\niface lo inet loopback\nallow-hotplug eth0\niface eth0 inet dhcp\n')
    put(root,'usr/bin/t95h-dns-init','#!/bin/sh\nmkdir -p /tmp\nprintf "nameserver 1.1.1.1\\n" > /tmp/resolv.conf\n',0o755)
    put(root,'etc/systemd/system/t95h-dns-init.service','[Unit]\nBefore=networking.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/t95h-dns-init\n[Install]\nWantedBy=multi-user.target\n')
    release=(o/'kernel/include/config/kernel.release').read_text().strip()
    run('rsync','-a',str(o/'modules/root/lib/modules')+'/',str(root/'lib/modules')+'/')
    hw=root/'usr/lib/t95h'; hw.mkdir(parents=True,exist_ok=True)
    for name in ['t95h_aldo2.ko','t95h_ana_provider.ko']:
        candidates=list((root/'lib/modules'/release).rglob(name))
        if len(candidates)!=1: raise ValueError('Missing private hardware module '+name)
        shutil.move(candidates[0],hw/name)
    run('depmod','-b',root,release)
    for entry in json.loads((ROOT/'boards/t95h/profiles/integration-draft.json').read_text())['firmware']:
        if entry['profile'] not in ['base','B']: continue
        rel=entry['file']; src=fw/rel
        if sha(src)!=entry['sha256']: raise ValueError('Firmware mismatch '+rel)
        dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
    start=(ROOT/'boards/t95h/libreelec/hardware/start-hardware').read_text().replace('7.2.3-t95h-libreelec',release).replace('Kodi may start','kiosk may start')
    put(root,'usr/lib/t95h/start-hardware',start,0o755)
    unit=(ROOT/'boards/t95h/libreelec/hardware/system.d/t95h-hardware.service').read_text().replace('kodi.service','lightdm.service')
    put(root,'etc/systemd/system/t95h-hardware.service',unit)
    put(root,'etc/systemd/system/lightdm.service.d/t95h.conf','[Unit]\nRequires=t95h-hardware.service\nAfter=t95h-hardware.service\n')
    # Keep Xradio cold during the initial kiosk test; Ethernet/USB input remain available.
    dtb=o/'modules/startup/t95h.dtb'
    run('fdtput','-t','s',dtb,'/soc/mmc@4021000','status','disabled')
    for unit in ['t95h-hardware','t95h-dns-init']:
        run('systemctl','--root',root,'enable',unit)
    for f in (root/'etc/ssh').glob('ssh_host_*'): f.unlink()
    put(root,'etc/machine-id','')
    (root/'var/lib/dbus/machine-id').unlink(missing_ok=True)
    (root/'var/lib/dbus/machine-id').symlink_to('/etc/machine-id')
    (root/'usr/sbin/policy-rc.d').unlink()
    ssh_files=['usr/bin/kiosk-ssh-keys','etc/systemd/system/kiosk-ssh-keys.service','etc/ssh/sshd_config.d/kiosk.conf']
    for rel in ssh_files:
        if sha(root/rel)!=sha(o/'upstream/kiosk_skeleton'/rel): raise ValueError('Upstream SSH behavior changed: '+rel)
    for pattern in ['ssh_host_*','authorized_keys','id_rsa','id_ed25519']:
        if list((root/'boot/firmware').glob(pattern)): raise ValueError('SSH identity in public image')
    request['ssh_upstream_files']={rel:sha(root/rel) for rel in ssh_files}
    conf=root/'boot/firmware/kioskbrowser.ini'
    text=conf.read_text().replace('hostname = "kioskpi"','hostname = "t95h-kiosk"').replace('ssid="My WiFi"','ssid=""').replace('psk="My Passphrase"','psk=""')
    conf.write_text(text)
    out=o/'release'; out.mkdir()
    put(out,'prefix.bin', '')
    (out/'prefix.bin').write_bytes(prefix((inputs/'prefix.bin').read_bytes()))
    fat=o/'boot.fat'; ext=o/'root.ext4'
    with fat.open('wb') as f: f.truncate(128*M)
    with ext.open('wb') as f: f.truncate(6144*M)
    run('mkfs.vfat','-F','32','-n','T95HKIOSK','-i',DISK,fat)
    boot=root/'boot/firmware/boot'; boot.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(o/'kernel/arch/arm64/boot/Image',boot/'Image'); shutil.copyfile(dtb,boot/'t95h.dtb')
    script=(ROOT/'boards/t95h/boot/scripts/boot.scm.txt').read_text()
    script=re.sub(r'^setenv bootargs .*$',f'setenv bootargs console=ttyS0,115200 console=tty0 loglevel=7 root=PARTUUID={DISK}-02 rootwait rootfstype=ext4 ro net.ifnames=0',script,flags=re.M)
    put(o,'boot.txt',script)
    run('mkimage','-A','arm64','-T','script','-C','none','-n','T95H AnotterKiosk','-d',o/'boot.txt',boot/'boot.scm')
    for dest in [boot/'boot.scr',root/'boot/firmware/boot.scr']:
        shutil.copyfile(ROOT/'boards/t95h/boot/scripts/boot.scr',dest)
    bootfiles=list((root/'boot/firmware').iterdir())
    run('mcopy','-s','-i',fat,*bootfiles,'::/')
    for file in (root/'boot/firmware').rglob('*'):
        if not file.is_file(): continue
        run('mcopy','-o','-i',fat,'::/'+str(file.relative_to(root/'boot/firmware')),o/'readback')
        if sha(o/'readback')!=sha(file): raise ValueError('FAT readback mismatch')
    for item in bootfiles:
        if item.is_dir(): shutil.rmtree(item)
        else: item.unlink()
    run('mkfs.ext4','-F','-L','T95HROOT','-d',root,ext)
    run('e2fsck','-fn',ext); run('fsck.vfat','-n',fat)
    name=f'T95H-AnotterKiosk-{tag}-arm64-sd.img.gz'; h=hashlib.sha256()
    with (out/name).open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=lock['epoch'],compresslevel=3) as z:
        for part in [out/'prefix.bin',fat,ext]:
            with part.open('rb') as source:
                while data:=source.read(M): h.update(data); z.write(data)
    with gzip.open(out/name,'rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=h.hexdigest(): raise ValueError('Image compression mismatch')
    (out/'prefix.bin').unlink()
    request.update(kernel=release,kernel_sha256=sha(o/'kernel/arch/arm64/boot/Image'),dtb_sha256=sha(dtb),image=name,sha256=sha(out/name),raw_sha256=h.hexdigest(),raw_bytes=(4+128+6144)*M)
    put(out,'manifest.json',json.dumps(request,indent=2)+'\n')
    shutil.copyfile(o/'packages.tsv',out/'packages.tsv'); shutil.copyfile(o/'kernel/.config',out/'kernel.config')
    shutil.copyfile(ROOT/'docs/anotter-kiosk.md',out/'RELEASE-NOTES.md')
    put(out,'SHA256SUMS',sha(out/name)+'  '+name+'\n')
    print('PASS: experimental SD image assembled; hardware validation pending',flush=True)
if __name__=='__main__': main()
