#!/usr/bin/env python3
"""Check source locks and profile contracts without building or touching a device."""
import hashlib,json,subprocess,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
    board=ROOT/'boards/t95h'
    scripts=board/'boot/scripts'
    for name, sha in json.loads((scripts/'sha256.json').read_text()).items():
        assert digest(scripts/name)==sha, 'Boot script hash mismatch: '+name
    baseline=json.loads((board/'baseline.json').read_text())
    k=json.loads((board/'kernel/source-lock.json').read_text())
    assert digest(board/'kernel'/k['patch'])==k['patch_sha256'], 'Kernel patch hash mismatch'
    w=baseline['wlan']
    assert digest(board/w['incremental_patch'])==w['incremental_patch_sha256'], 'WLAN patch hash mismatch'
    dt=json.loads((board/'dts/source-lock.json').read_text())
    for key in ['source','inventory']:
        assert digest(board/'dts'/dt[key])==dt[key+'_sha256'], 'DT lock mismatch'
    ext=json.loads((board/'external/source-lock.json').read_text())
    for name,entry in ext['files'].items():
        assert digest(board/'external'/name)==entry['source_sha256'], 'External source mismatch: '+name
    for profile in baseline['profiles']:
        cfg=(board/'profiles/kconfig-draft'/(profile+'.config')).read_text()
        for option in ['CONFIG_PCI','CONFIG_BLK_DEV_NVME','CONFIG_MHI_BUS']:
            assert option+'=y' not in cfg and option+'=m' not in cfg, profile+': '+option
        assert 'CONFIG_XRADIO=y' in cfg, profile+': internal WLAN missing'
        assert 'CONFIG_SND=y' in cfg, profile+': base audio missing'
        assert 'CONFIG_DRM=y' in cfg, profile+': base display missing'
    runtime=json.loads((board/'openwrt/runtime-lock.json').read_text())
    expected=set(runtime['files'])
    actual={str(p.relative_to(board)) for p in (board/'openwrt/runtime').rglob('*') if p.is_file()}
    assert actual==expected, 'Runtime inventory mismatch'
    for name, entry in runtime['files'].items():
        p=board/name
        assert not p.is_symlink() and digest(p)==entry['sha256'], 'Runtime hash mismatch: '+name
        assert (p.stat().st_mode & 0o777)==int(entry['mode'],8), 'Runtime permissions mismatch: '+name
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    for name in filter(None,tracked):
        p=ROOT/name
        assert not p.is_symlink(), 'Review symlink before distribution: '+name
        assert p.stat().st_size<10*1024*1024, 'Unexpected binary/large file: '+name
        if p.suffix in ('.py','.sh','.yml','.md','.json','.c','.h','.dts'):
            raw=p.read_bytes()
            assert (b'-----BEGIN '+b'OPENSSH PRIVATE KEY-----') not in raw, name
            assert (b'-----BEGIN '+b'RSA PRIVATE KEY-----') not in raw, name
    return {'repository_checks_passed':True,'baseline':baseline['id'],
            'profiles':baseline['profiles'],'full_image_build_ready':False,
            'hardware_validation':'not implied by repository checks'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    result=check()
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
