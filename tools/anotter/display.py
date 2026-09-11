#!/usr/bin/env python3
"""Apply and verify the Anotter-only, live-tested DE33 source/DT pairing."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / 'boards/t95h/anotter/de33'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def manifest():
    lock = json.loads((BUNDLE / 'lock.json').read_text())
    if digest(BUNDLE / 'display.patch') != lock['patch_sha256']:
        raise ValueError('DE33 patch checksum mismatch')
    return lock

def verify(tree, state='after'):
    lock = manifest()
    for name, expected in lock[state].items():
        if digest(tree / name) != expected:
            raise ValueError('DE33 source differs: ' + name)
    return lock

def apply(stage):
    report_path = stage / 'source-report.json'
    report = json.loads(report_path.read_text())
    lock = manifest()
    if not report['source_preparation_passed'] or report['kernel'] != lock['kernel'] or 'display_variant' in report:
        raise ValueError('Expected a fresh verified baseline source')
    tree = stage / ('linux-' + lock['kernel'])
    verify(tree, 'before')
    subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', str(BUNDLE / 'display.patch')], cwd=tree, check=True)
    verify(tree)
    report['display_variant'] = 'anotter-de33'
    report['display_patch_sha256'] = lock['patch_sha256']
    report_path.write_text(json.dumps(report, indent=2) + '\n')

def dtb(path):
    # Preserve all other properties, especially clocks, thermal limits and boot media.
    import libfdt
    dt = libfdt.Fdt(path.read_bytes())
    dt.resize(len(path.read_bytes()) + 1024)
    mixer = dt.path_offset('/soc/bus@1000000/mixer@280000')
    planes = dt.path_offset('/soc/bus@1000000/planes@100000')
    ref = bytes(dt.getprop(mixer, 'iommus'))
    if len(ref) != 8 or int.from_bytes(ref[4:], 'big') != 0:
        raise ValueError('Unexpected mixer IOMMU reference')
    try:
        dt.getprop(planes, 'iommus')
    except libfdt.FdtException as e:
        if e.err != -libfdt.NOTFOUND: raise
    else:
        raise ValueError('Planes already have an IOMMU binding')
    dt.setprop(planes, 'iommus', ref)
    dt.delprop(dt.path_offset('/soc/bus@1000000/mixer@280000'), 'iommus')
    dt.pack()
    path.write_bytes(dt.as_bytearray())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['apply', 'verify', 'dtb'])
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    globals()[args.mode](args.path.resolve())
