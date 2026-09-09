#!/usr/bin/env python3
"""Build the locked full T95H DT and verify semantic identity; no device access."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
import libfdt

def inventory(path):
    f=libfdt.Fdt(path.read_bytes()); nodes={}
    def walk(off,path):
        props={}; p=f.first_property_offset(off,quiet=(libfdt.NOTFOUND,))
        while p>=0:
            v=f.get_property_by_offset(p); props[v.name]=bytes(v).hex()
            p=f.next_property_offset(p,quiet=(libfdt.NOTFOUND,))
        nodes[path]=props; child=f.first_subnode(off,quiet=(libfdt.NOTFOUND,))
        while child>=0:
            walk(child,path.rstrip('/')+'/'+f.get_name(child))
            child=f.next_subnode(child,quiet=(libfdt.NOTFOUND,))
    walk(0,'/')
    return {'nodes':nodes,'reservations':[list(f.get_mem_rsv(i)) for i in range(f.num_mem_rsv())], 'boot_cpuid_phys':f.boot_cpuid_phys()}

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--output',required=True,type=Path); args=ap.parse_args()
    base=Path(__file__).resolve().parents[1]/'boards/t95h/dts'
    lock=json.loads((base/'source-lock.json').read_text())
    for name in ('source','inventory'):
        path=base/lock[name]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=lock[name+'_sha256']:
            raise SystemExit('STOP: '+name+' hash differs from lock')
    output=args.output.absolute()
    if output.exists() or output.is_symlink():raise SystemExit('STOP: output already exists; choose a new file')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dtb-check-',dir=output.parent) as tmp:
        built=Path(tmp)/'tree.dtb'
        subprocess.run(['dtc','-q','-I','dts','-O','dtb','-o',str(built),str(base/lock['source'])],check=True)
        if inventory(built)!=json.loads((base/lock['inventory']).read_text()):
            raise SystemExit('STOP: rebuilt tree differs from locked reference')
        data=built.read_bytes()
        with output.open('xb') as f:f.write(data)
    print(json.dumps({'passed':True,'output':str(output),'sha256':hashlib.sha256(data).hexdigest(),'semantic_reference_match':True,'hardware_tested':False,'dtc':subprocess.check_output(['dtc','--version'],text=True).strip()},indent=2))
if __name__=='__main__':main()
