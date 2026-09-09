#!/usr/bin/env python3
"""Prepare a conservative eMMC-access DTB from the current SD DTB; no device writes."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import libfdt

NODE = '/soc/mmc@4022000'
SET = {'status': b'okay\0', 'bus-width': struct.pack('>I', 8),
       'max-frequency': struct.pack('>I', 25000000), 'non-removable': b'',
       'no-sd': b'', 'no-sdio': b'', 'voltage-ranges': struct.pack('>II',3300,3300)}
REMOVE = ('cap-sd-highspeed','cap-mmc-highspeed','mmc-ddr-3_3v','cap-sdio-irq')
spec = importlib.util.spec_from_file_location('dt_inventory', Path(__file__).resolve().parents[1] / 'build-tested-dtb.py')
inventory_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_module)

def prepare(source, output):
    if output.exists(): raise ValueError('Output already exists')
    before = inventory_module.inventory(source)
    props = before['nodes'][NODE]
    if '616c6c77696e6e65722c73756e3530692d683631362d656d6d63' not in props['compatible']:
        raise ValueError('Unexpected eMMC controller')
    raw = source.read_bytes(); tree = libfdt.Fdt(raw); tree.resize(len(raw)+2048)
    off = tree.path_offset(NODE)
    for key in REMOVE:
        if key in props: tree.delprop(off,key)
    for key,value in SET.items(): tree.setprop(off,key,value)
    tree.pack()
    output.write_bytes(bytes(tree.as_bytearray()))
    after = inventory_module.inventory(output)
    expected = json.loads(json.dumps(before))
    for key in REMOVE: expected['nodes'][NODE].pop(key,None)
    expected['nodes'][NODE].update({k:v.hex() for k,v in SET.items()})
    if after != expected:
        output.unlink(); raise ValueError('Unexpected DT changes')
    return {'source_sha256':hashlib.sha256(raw).hexdigest(),
            'test_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'only_emmc_node_changed':True, 'emmc_writes':False,
            'note':'Enables controller access only. Does not make the SD image eMMC-bootable. No regulator setting changed.'}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.source,a.output),indent=2))
