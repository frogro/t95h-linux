#!/usr/bin/env python3
"""Apply locked PMIC-corrected SPL; retain legacy recipe and all later firmware."""
import argparse, hashlib, importlib.util, json, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def prepare(source, output, medium):
    assets=ROOT/'boards/t95h/boot/pmic305'
    lock=json.loads((assets/'lock.json').read_text())[medium]
    old=source.read_bytes()
    if medium=='emmc':
        spec=importlib.util.spec_from_file_location('legacy_prefix',Path(__file__).with_name('prepare-boot-prefix.py'))
        legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
        with tempfile.TemporaryDirectory() as tmp:
            derived=Path(tmp)/'prefix.bin';legacy.prepare(source,derived);old=derived.read_bytes()
    if hashlib.sha256(old).hexdigest()!=lock['legacy_prefix_sha256']:
        raise ValueError('Unknown original boot prefix')
    spl=(assets/(medium+'.toc0')).read_bytes()
    if len(spl)!=40960 or hashlib.sha256(spl).hexdigest()!=lock['spl_sha256']:
        raise ValueError('Corrected SPL mismatch')
    data=bytearray(old);data[8192:49152]=spl
    if hashlib.sha256(data).hexdigest()!=lock['prefix_sha256']:
        raise ValueError('Corrected prefix mismatch')
    with output.open('xb') as f:f.write(data)
    return lock
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--medium',choices=['sd','emmc'],required=True)
    a=p.parse_args();prepare(a.source,a.output,a.medium)
