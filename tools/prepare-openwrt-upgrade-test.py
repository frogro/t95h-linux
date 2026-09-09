#!/usr/bin/env python3
"""Upload checked artifacts and install the upgrade hook; only sysupgrade -T, no flash/reboot."""
import argparse,getpass,hashlib,json,shlex,sys
from pathlib import Path
import paramiko
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--host',default='192.168.178.177');p.add_argument('--verify-only',action='store_true');a=p.parse_args();b=a.build.resolve()
proof=json.loads((b/'build-proof.json').read_text());tests=json.loads((b/'upgrade-test.json').read_text())
assert tests['passed'] and tests['sysupgrade_sha256']==proof['sysupgrade_sha256']
keep=b/'t95h-keep'
if not keep.is_file():keep=Path(__file__).resolve().parents[1]/'boards/t95h/openwrt/upgrade/t95h-keep'
files=[(b/proof['sysupgrade'],'/tmp/t95h-sysupgrade.bin',proof['sysupgrade_sha256']),(b/'platform.sh','/tmp/t95h-platform.sh',proof['platform_sha256']),(keep,'/tmp/t95h-upgrade-keep',proof['keep_sha256'])]
for src,_,expected in files:
 with src.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
 if expected:assert actual==expected,src
if a.verify_only:
 print('PASS: Paket, Hook und Erhaltungsliste stimmen mit dem geprüften Build überein. Kein SSH-Zugriff.');sys.exit(0)
c=paramiko.SSHClient();c.load_system_host_keys();c.load_host_keys(str(Path.home()/'.ssh/known_hosts'))
c.connect(a.host,username='root',password=getpass.getpass('SSH-Passwort für root: '),allow_agent=False,look_for_keys=False,timeout=10)
def execute(cmd,timeout=600):
 channel=c.get_transport().open_session(timeout=timeout)
 channel.settimeout(timeout);channel.set_combine_stderr(True);channel.exec_command(cmd)
 import codecs
 decoder=codecs.getincrementaldecoder('utf-8')(errors='replace')
 try:
  while data:=channel.recv(65536):
   print(decoder.decode(data),end='',flush=True)
  print(decoder.decode(b'',final=True),end='',flush=True)
  rc=channel.recv_exit_status()
 finally:channel.close()
 if rc:raise RuntimeError(f'Remote command failed: {rc}')

try:
 execute("test $(id -u) = 0 && test -r /proc/device-tree/compatible && grep -q t95h /proc/device-tree/compatible && df -h /tmp")
 for src,dst,expected in files:
  expected=expected or hashlib.sha256(src.read_bytes()).hexdigest()
  print('Übertrage '+src.name,flush=True)
  i,o,e=c.exec_command('umask 077; test ! -L '+shlex.quote(dst)+' && cat > '+shlex.quote(dst),timeout=300)
  with src.open('rb') as f:
   while data:=f.read(262144):i.write(data)
  i.flush();i.channel.shutdown_write();out=o.read();err=e.read();rc=o.channel.recv_exit_status();i.close();o.close();e.close();assert rc==0,(out,err)
  execute('echo '+shlex.quote(expected+'  '+dst)+' | sha256sum -c -')
 # First check runs directly from /tmp and does not replace any installed files.
 execute("ash -c '. /tmp/t95h-platform.sh; t95h_validate_payload /tmp/t95h-sysupgrade.bin && platform_check_image /tmp/t95h-sysupgrade.bin'")
 execute(r'''set -e
backup=/root/t95h-upgrade-hook-backup-$(date -u +%Y%m%dT%H%M%SZ)
umask 077
mkdir "$backup"
cp -p /lib/upgrade/platform.sh "$backup/platform.sh"
if [ -e /lib/upgrade/keep.d/t95h ]; then cp -p /lib/upgrade/keep.d/t95h "$backup/keep"; fi
cat > "$backup/restore.sh" <<'RESTORE'
#!/bin/sh
set -e
here=$(dirname "$0")
cp -p "$here/platform.sh" /lib/upgrade/platform.sh
if [ -f "$here/keep" ]; then cp -p "$here/keep" /lib/upgrade/keep.d/t95h; else rm -f /lib/upgrade/keep.d/t95h; fi
sync
RESTORE
chmod 700 "$backup/restore.sh"
mkdir -p /lib/upgrade/keep.d
cp /tmp/t95h-platform.sh /lib/upgrade/platform.sh
cp /tmp/t95h-upgrade-keep /lib/upgrade/keep.d/t95h
chmod 644 /lib/upgrade/platform.sh /lib/upgrade/keep.d/t95h
if ! sysupgrade -T /tmp/t95h-sysupgrade.bin; then sh "$backup/restore.sh"; exit 1; fi
sync
echo "PASS: sysupgrade -T erfolgreich. Hook-Sicherung: $backup"
echo 'Kein Upgrade ausgeführt, kein Neustart.'
''')
 print('\nNächster Schritt AUF DER BOX (schreibt Partitionen und startet neu):\nsysupgrade /tmp/t95h-sysupgrade.bin')
finally:c.close()
