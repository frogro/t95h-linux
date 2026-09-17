#!/usr/bin/env python3
"""Shared, pinned DI300 driver and effective-DTB integration for T95H images."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'tools/experimental/di300'
NODE = '/soc/deinterlace@1420000'
DT_COMMIT = '7c3bec1204dfae17ad1bc9cb476e6d84e71b2768'


def patches(api):
    if api not in ('7.2', '6.12'):
        raise ValueError('Unreviewed DI300 kernel API')
    lock = json.loads((BUNDLE / 'manifest.json').read_text())
    # The board builders use an effective DTB or OpenWrt multimedia overlay,
    # not the generic upstream DTS. Install the equivalent node there instead.
    items = [x for x in lock['series'] if x['commit'] != DT_COMMIT]
    if api == '6.12':
        items.append(lock['compat_6_12'])
    result = []
    for item in items:
        path = BUNDLE / item['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('DI300 patch checksum mismatch: ' + str(path))
        result.append((path, item['sha256']))
    return result


def apply_source(source, api):
    selected = patches(api)
    for path, _ in selected:
        subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1',
                        '-i', str(path)], cwd=source, check=True)
    return [digest for _, digest in selected]


def cells(*values):
    return struct.pack('>' + 'I' * len(values), *values)


def properties(dt):
    def phandle(path):
        return dt.getprop(dt.path_offset(path), 'phandle').as_uint32()
    ccu = phandle('/soc/clock@3001000')
    iommu = phandle('/soc/iommu@30f0000')
    # H616 CCU binding IDs: BUS_DEINTERLACE=32, DEINTERLACE=31,
    # RST_BUS_DEINTERLACE=2. IOMMU master 1 belongs to DI300.
    return {'compatible': b'allwinner,sun50i-h616-deinterlace\0',
            'reg': cells(0x01420000, 0x40000),
            'clocks': cells(ccu, 32, ccu, 31),
            'clock-names': b'bus\0mod\0', 'resets': cells(ccu, 2),
            'interrupts': cells(0, 89, 4), 'iommus': cells(iommu, 1),
            'status': b'okay\0'}


def verify_dtb(path):
    import libfdt
    dt = libfdt.Fdt(Path(path).read_bytes())
    off = dt.path_offset(NODE)
    for key, value in properties(dt).items():
        if bytes(dt.getprop(off, key)) != value:
            raise ValueError('DI300 DT mismatch: ' + key)
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add_dtb(path):
    import libfdt
    path = Path(path)
    raw = path.read_bytes()
    dt = libfdt.Fdt(raw)
    props = properties(dt)
    try:
        dt.path_offset(NODE)
    except libfdt.FdtException as error:
        if error.err != -libfdt.NOTFOUND:
            raise
    else:
        raise ValueError('DI300 node already present; refusing to replace it')
    dt.resize(len(raw) + 2048)
    dt.add_subnode(dt.path_offset('/soc'), 'deinterlace@1420000')
    for key, value in props.items():
        dt.setprop(dt.path_offset(NODE), key, value)
    dt.pack()
    path.write_bytes(bytes(dt.as_bytearray()))
    return verify_dtb(path)
