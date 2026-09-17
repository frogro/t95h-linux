#!/usr/bin/env python3
"""Offline T95H Anotter SD image refresh, retaining the supported FAT settings.
Run on a Linux PC, never against a mounted/live system. No full old-image backup.
"""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile

M = 1048576
SETTINGS = ('kioskbrowser.ini', 'wpa_supplicant.conf', 'authorized_keys', 'id_rsa',
            'id_ed25519', 'ssh_host_rsa_key', 'ssh_host_rsa_key.pub',
            'ssh_host_ed25519_key', 'ssh_host_ed25519_key.pub', 'splash.png', 'www-public')


def run(*args):
    subprocess.run([str(x) for x in args], check=True)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def sd_layout(header):
    if len(header) < 512 or header[510:512] != b'\x55\xaa':
        raise ValueError('Keine MBR-SD')
    if struct.unpack_from('<I', header, 440)[0] != 0xa0950001:
        raise ValueError('Kein T95H-Anotter-SD-Image; eMMC und fremde Systeme abgelehnt')
    start, sectors = struct.unpack_from('<II', header, 454)
    if (start, sectors) != (8192, 262144):
        raise ValueError('Unerwartete Anotter-Bootpartition')
    return start * 512, sectors * 512


def image_entry(manifest, name):
    if manifest.get('image') == name:
        return {'sha256': manifest['sha256'], 'raw_sha256': manifest['raw_sha256']}
    entry = manifest.get('sd_emmc_installer', {})
    if entry.get('file') == name:
        return entry
    raise ValueError('Nur SD solo oder kombinierte SD aus diesem Manifest erlaubt')


def read_fat(stream, dest):
    stream.seek(0)
    offset, size = sd_layout(stream.read(512))
    stream.seek(offset)
    with dest.open('xb') as out:
        for _ in range(size // M):
            data = stream.read(M)
            if len(data) != M:
                raise ValueError('Bootpartition unvollständig')
            out.write(data)
    return offset, size


def snapshot(fat, settings, scratch):
    # mcopy exits on corrupt FAT; do not silently treat read errors as absent settings.
    scratch.mkdir()
    run('mcopy', '-s', '-i', fat, '::*', scratch)
    if not (scratch / 'kioskbrowser.ini').is_file() or not (scratch / 'boot/boot.scm').is_file():
        raise ValueError('Vorhandenes Anotter-System nicht erkannt')
    settings.mkdir(mode=0o700)
    for name in SETTINGS:
        source = scratch / name
        if source.exists():
            if source.is_dir():
                shutil.copytree(source, settings / name)
            else:
                shutil.copyfile(source, settings / name)
    if sum(p.stat().st_size for p in settings.rglob('*') if p.is_file()) > 90 * M:
        raise ValueError('Einstellungen größer als 90 MiB')
    return {str(p.relative_to(settings)): sha(p) for p in settings.rglob('*') if p.is_file()}


def restore(fat, settings, scratch):
    for source in settings.iterdir():
        if source.name in SETTINGS:
            run('mcopy', '-s', '-o', '-i', fat, source, '::/')
    scratch.mkdir()
    run('mcopy', '-s', '-i', fat, '::*', scratch)
    for source in settings.rglob('*'):
        if source.is_file() and source.relative_to(settings).parts[0] in SETTINGS and sha(source) != sha(scratch / source.relative_to(settings)):
            raise ValueError('Konfigurations-Rückleseprüfung fehlgeschlagen')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--device', type=Path, required=True)
    parser.add_argument('--settings-dir', type=Path, required=True,
                        help='Neues privates Verzeichnis auf dem PC für die Konfigurationssicherung')
    parser.add_argument('--work-dir', type=Path, required=True,
                        help='PC-Verzeichnis mit mindestens 9 GB freiem Platz')
    args = parser.parse_args()
    os.umask(0o077)
    if os.geteuid() != 0 or not os.isatty(0):
        raise ValueError('Interaktiv mit sudo auf dem Linux-PC starten')
    if args.settings_dir.exists():
        raise ValueError('Für jeden Lauf ein neues Einstellungsverzeichnis verwenden')
    entry = image_entry(json.loads(args.manifest.read_text()), args.image.name)
    if sha(args.image) != entry['sha256']:
        raise ValueError('Download-Prüfsumme falsch')
    device = args.device.resolve(strict=True)
    info = device.stat()
    if not stat.S_ISBLK(info.st_mode):
        raise ValueError('Ziel ist kein Blockgerät')
    sysdev = Path('/sys/dev/block') / f'{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}'
    if (sysdev / 'partition').exists() or (sysdev / 'removable').read_text().strip() != '1':
        raise ValueError('Nur eine komplette, wechselbare SD zulässig')
    # O_EXCL on a block device refuses mounted partitions and active holders.
    # Keep the same descriptor across snapshot/write/readback to prevent path races.
    with os.fdopen(os.open(device, os.O_RDWR | os.O_EXCL), 'r+b', buffering=0) as target:
        capacity = struct.unpack('Q', fcntl.ioctl(target, 0x80081272, bytes(8)))[0]
        with tempfile.TemporaryDirectory(prefix='anotter-update-', dir=args.work_dir) as temp:
            work = Path(temp)
            raw = work / 'new.img'
            with gzip.open(args.image, 'rb') as source, raw.open('xb') as dest:
                shutil.copyfileobj(source, dest, M)
            if sha(raw) != entry['raw_sha256'] or raw.stat().st_size > capacity:
                raise ValueError('Entpacktes Image beschädigt oder SD zu klein')
            with raw.open('rb') as source:
                offset, size = read_fat(source, work / 'new.fat')
            read_fat(target, work / 'old.fat')
            hashes = snapshot(work / 'old.fat', args.settings_dir, work / 'old-files')
            (args.settings_dir / 'settings-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
            restore(work / 'new.fat', args.settings_dir, work / 'new-files')
            with raw.open('r+b') as dest, (work / 'new.fat').open('rb') as source:
                dest.seek(offset)
                shutil.copyfileobj(source, dest, M)
            expected = sha(raw)
            os.sync()  # Persist the settings recovery copy BEFORE replacing the SD.
            print(f'Ziel: {device}, {capacity} Byte. Neues Image: {args.image.name}')
            print(f'Einstellungen gesichert und im neuen Image geprüft: {args.settings_dir}')
            if input('SD wird ersetzt. Zum Schreiben SD UPDATE eingeben: ') != 'SD UPDATE':
                raise ValueError('Abgebrochen; SD unverändert')
            target.seek(0)
            with raw.open('rb') as source:
                while data := source.read(M):
                    view = memoryview(data)
                    while view:
                        written = target.write(view)
                        if not written:
                            raise OSError('SD-Schreibfehler')
                        view = view[written:]
            os.fsync(target.fileno())
            fcntl.ioctl(target, 0x1261)  # BLKFLSBUF: actual device readback, not page cache.
            target.seek(0)
            remaining = raw.stat().st_size
            digest = hashlib.sha256()
            while remaining:
                data = target.read(min(M, remaining))
                if not data:
                    raise ValueError('SD-Rückleseprüfung unvollständig')
                digest.update(data)
                remaining -= len(data)
            if digest.hexdigest() != expected:
                raise ValueError('SD-Rückleseprüfung fehlgeschlagen; Einstellungen bleiben gesichert')
            print('FERTIG: Neues Image und Einstellungen vollständig zurückgelesen. Karte entfernen.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'STOP: {error}')
