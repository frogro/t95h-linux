#!/usr/bin/env python3
"""Run generated shell against mocks: credentials remain data, never shell code."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('access', root / 'installer/access.py')
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)
with tempfile.TemporaryDirectory() as temp:
    directory = Path(temp)
    password = "test' ; $(touch UNEXPECTED) `touch OTHER` : end"
    script = directory / 'setup.sh'
    script.write_text(access.render("test' AP", 'abcdefgh', password))
    for command, body in {
        'chpasswd': '#!/bin/sh\ncat > "$CAPTURE/password"\n',
        'uci': '#!/bin/sh\nprintf "%s\\n" "$@" >> "$CAPTURE/uci.log"\n',
    }.items():
        path = directory / command
        path.write_text(body)
        path.chmod(0o755)
    env = dict(os.environ, PATH=str(directory)+':'+os.environ['PATH'], CAPTURE=temp)
    subprocess.run(['sh', str(script)], cwd=temp, env=env, check=True)
    assert (directory/'password').read_text() == 'root:'+password+'\n'
    assert 'ttyd.@ttyd[0].credential=root:'+password+'\n' in (directory/'uci.log').read_text()
    assert not (directory/'UNEXPECTED').exists()
    assert not (directory/'OTHER').exists()
    for values in [('ssid','short','root'), ('ssid','abcdefgh',''), ('ssid','abcdefgh','x\ny')]:
        try:
            access.render(*values)
        except ValueError:
            continue
        raise AssertionError('Invalid credentials accepted')
    (directory/'uci.log').unlink()
    script.write_text(access.render('', '', password, ap_enabled=False))
    subprocess.run(['sh', str(script)], cwd=temp, env=env, check=True)
    recorded = (directory/'uci.log').read_text()
    assert 'wireless.ap.disabled=1' in recorded
    assert 'dhcp.wlan.ignore=1' in recorded
    assert 'wireless.ap.key=' not in recorded
    assert 'network.lan' not in recorded
    # Independent defaults: custom SSH password need not change AP defaults.
    with patch('builtins.input', side_effect=['', '']), patch('getpass.getpass', side_effect=['custom-root', 'custom-root', '']), patch('builtins.print'):
        access.prepare(directory/'defaults')
    result_script = (directory/'defaults/private/firstboot/99-t95h-local-access').read_text()
    assert 'root:custom-root' in result_script and 'wireless.ap.key=openwrtopenwrt' in result_script
    with patch('builtins.input', side_effect=['n']), patch('getpass.getpass', side_effect=['']), patch('builtins.print'):
        access.prepare(directory/'no-ap')
    result_script = (directory/'no-ap/private/firstboot/99-t95h-local-access').read_text()
    assert 'root:openwrt' in result_script and 'wireless.ap.disabled=1' in result_script
    # A failed password update must stop before any UCI changes.
    (directory/'uci.log').unlink()
    (directory/'chpasswd').write_text('#!/bin/sh\nexit 1\n')
    result = subprocess.run(['sh', str(script)], cwd=temp, env=env)
    assert result.returncode != 0 and not (directory/'uci.log').exists()
print('PASS: local access quoting, validation and failure handling')
