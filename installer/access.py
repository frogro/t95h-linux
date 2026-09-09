"""Local-only first-boot access settings; never a workflow input."""
import getpass
import os
import shlex
from pathlib import Path


def render(ssid, wifi_password, root_password, ap_enabled=True):
    for value in (ssid, wifi_password, root_password):
        if any(c in value for c in '\x00\r\n'):
            raise ValueError('Zeilenumbrüche und NUL sind nicht erlaubt.')
    if ap_enabled and not 1 <= len(ssid.encode()) <= 32:
        raise ValueError('SSID muss 1–32 UTF-8-Bytes enthalten.')
    if ap_enabled and (not 8 <= len(wifi_password) <= 63 or not wifi_password.isascii()):
        raise ValueError('WLAN-Passwort muss 8–63 ASCII-Zeichen enthalten.')
    if not root_password:
        raise ValueError('Root-Passwort darf nicht leer sein.')
    q = shlex.quote
    ap_commands = [
        'uci set wireless.ap.disabled=' + ('0' if ap_enabled else '1') + ' || exit 1',
        'uci set dhcp.wlan.ignore=' + ('0' if ap_enabled else '1') + ' || exit 1',
    ]
    if ap_enabled:
        ap_commands += [
            'uci set wireless.radio0.disabled=0 || exit 1',
            'uci set ' + q('wireless.ap.ssid=' + ssid) + ' || exit 1',
            'uci set ' + q('wireless.ap.key=' + wifi_password) + ' || exit 1',
        ]
    return '\n'.join([
        '#!/bin/sh',
        '# Lokale Erstkonfiguration: enthält Zugangsdaten. Nicht veröffentlichen.',
        "printf '%s\\n' " + q('root:' + root_password) + ' | chpasswd || exit 1',
        *ap_commands,
        'uci set ' + q('ttyd.@ttyd[0].credential=root:' + root_password) + ' || exit 1',
        'uci commit wireless || exit 1',
        'uci commit dhcp || exit 1',
        'uci commit ttyd || exit 1',
        'exit 0', ''
    ])


def prepare(root: Path):
    password = getpass.getpass('SSH/LuCI: Root-Passwort [Enter = openwrt]: ')
    if password:
        if password != getpass.getpass('Root-Passwort wiederholen: '):
            raise ValueError('Root-Passwörter stimmen nicht überein.')
    else:
        password = 'openwrt'
    choice = input('Möchten Sie zusätzlich einen WLAN-AP einrichten? [J/n]: ').strip().lower()
    if choice not in ('', 'j', 'ja', 'y', 'yes', 'n', 'nein', 'no'):
        raise ValueError('Bitte ja oder nein wählen.')
    enabled = choice not in ('n', 'nein', 'no')
    ssid, wifi = 'openwrt', 'openwrtopenwrt'
    if enabled:
        ssid = input('AP-Name (SSID) [openwrt]: ') or ssid
        selected = getpass.getpass('WLAN-Passwort [Enter = openwrtopenwrt]: ')
        if selected:
            if selected != getpass.getpass('WLAN-Passwort wiederholen: '):
                raise ValueError('WLAN-Passwörter stimmen nicht überein.')
            wifi = selected
    else:
        print('AP deaktiviert. Zugang über Ethernet; IP-Adresse per DHCP vom Router.')
    script = render(ssid, wifi, password, ap_enabled=enabled)
    directory = root / 'private' / 'firstboot'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    path = directory / '99-t95h-local-access'
    # Never silently overwrite a prior selection.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(script)
    print('Erstkonfiguration nur lokal gespeichert:', path)
    print('Noch nicht auf SD angewendet. Nicht in Actions oder ein öffentliches Image übernehmen.')
