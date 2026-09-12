#!/usr/bin/env python3
"""Package SD + compressed eMMC payload for Anotter/LibreELEC; no device writes."""
import argparse, gzip, hashlib, importlib.util, json, shutil, struct, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
M=1048576

def run(*a): subprocess.run(list(map(str,a)),check=True)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def unpack(src,dst):
    h=hashlib.sha256()
    with gzip.open(src,'rb') as a,dst.open('xb') as b:
        while data:=a.read(M):h.update(data);b.write(data)
    if sha(dst)!=h.hexdigest():raise ValueError('Extracted SD differs from compressed source')
def partition(prefix,index):
    return struct.unpack_from('<II',prefix,446+16*index+8)
def append_partition(prefix,raw_bytes,payload_bytes):
    if len(prefix)!=4*M or prefix[510:512]!=b'\x55\xaa' or any(prefix[478:510]):raise ValueError('Expected two-partition SD prefix')
    start,size=partition(prefix,1)
    if (start+size)*512!=raw_bytes or raw_bytes%M or payload_bytes%M:raise ValueError('Unexpected SD image layout')
    b=bytearray(prefix)
    b[478:494]=struct.pack('<B3sB3sII',0,b'\0'*3,131,b'\0'*3,raw_bytes//512,payload_bytes//512)
    return b

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('sd','emmc','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--os',choices=['anotter','libreelec'],required=True)
    p.add_argument('--compiler',default='aarch64-linux-gnu-gcc')
    a=p.parse_args();o=a.output.resolve();o.mkdir(parents=True,exist_ok=False)
    raw=o/'sd.img';unpack(a.sd,raw)
    with raw.open('rb') as f:prefix=f.read(4*M)
    if a.os=='libreelec':
        # Upstream first-boot resize extends p2 to the disk end. The installer
        # adds p3 there, so remove the marker only from this SD variant.
        offset,count=partition(prefix,1);storage=o/'storage.ext4'
        with raw.open('rb') as src,storage.open('wb') as dest:
            src.seek(offset*512);left=count*512
            while left:
                block=src.read(min(left,M))
                if not block:raise ValueError('Truncated storage partition')
                dest.write(block);left-=len(block)
        run('debugfs','-w','-R','rm /.please_resize_me',storage)
        check=subprocess.run(['debugfs','-R','stat /.please_resize_me',str(storage)],capture_output=True,text=True,check=True)
        if 'File not found' not in check.stderr:raise ValueError('Resize marker removal not verified')
        run('e2fsck','-fn',storage)
        with raw.open('r+b') as dest,storage.open('rb') as src:
            dest.seek(offset*512);shutil.copyfileobj(src,dest,M)
    start,sectors=partition(prefix,0)
    if start!=8192:raise ValueError('Unexpected FAT offset')
    fat=o/'boot.fat'
    with raw.open('rb') as f,fat.open('wb') as dest:
        f.seek(start*512);left=sectors*512
        while left:
            b=f.read(min(left,M))
            if not b:raise ValueError('Truncated SD')
            dest.write(b);left-=len(b)
    run('mcopy','-i',fat,'::/boot/t95h.dtb',o/'before.dtb')
    spec=importlib.util.spec_from_file_location('dt',ROOT/'tools/emmc/prepare-access-dtb.py');dt=importlib.util.module_from_spec(spec);spec.loader.exec_module(dt)
    dt.prepare(o/'before.dtb',o/'installer.dtb')
    run('mcopy','-o','-i',fat,o/'installer.dtb','::/boot/t95h.dtb')
    run('fsck.vfat','-n',fat)
    with raw.open('r+b') as f,fat.open('rb') as source:f.seek(start*512);shutil.copyfileobj(source,f,M)
    payload=o/'payload';payload.mkdir()
    shutil.copyfile(a.emmc,payload/'emmc.img.gz')
    with gzip.open(a.emmc,'rb') as f:
        h=hashlib.sha256();size=0
        while b:=f.read(M):h.update(b);size+=len(b)
    if size%M:raise ValueError('Unaligned eMMC image')
    (payload/'raw-bytes').write_text(str(size)+'\n');(payload/'raw-sha256').write_text(h.hexdigest()+'\n');(payload/'os').write_text(a.os+'\n')
    shutil.copyfile(ROOT/'boards/t95h/media-installer/install-emmc.sh',payload/'install-emmc.sh')
    for n in ('check-boot-selection','reread-partitions'):
        run(a.compiler,'-Os','-static',ROOT/'boards/t95h/emmc-installer'/(n+'.c'),'-o',payload/n)
    (payload/'SHA256SUMS').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(payload.iterdir())))
    part=o/'installer.ext4';partbytes=((sum(f.stat().st_size for f in payload.iterdir())+128*M+M-1)//M)*M
    with part.open('xb') as f:f.truncate(partbytes)
    run('mkfs.ext4','-q','-F','-L','T95HINSTALL','-O','^has_journal','-d',payload,part)
    run('e2fsck','-fn',part)
    for f in payload.iterdir():
        v=o/('verify-'+f.name);run('debugfs','-R',f'dump /{f.name} {v}',part)
        if sha(f)!=sha(v):raise ValueError('Payload readback differs')
    newprefix=append_partition(prefix,raw.stat().st_size,partbytes)
    with raw.open('r+b') as f:f.write(newprefix)
    name=a.sd.name.replace('-sd.img.gz','-sd-emmc-installer.img.gz')
    if name==a.sd.name:raise ValueError('Expected SD filename')
    h=hashlib.sha256();total=0
    with (o/name).open('xb') as dest,gzip.GzipFile(fileobj=dest,mode='wb',mtime=0,filename='',compresslevel=3) as gz:
        for src in (raw,part):
            with src.open('rb') as f:
                while b:=f.read(M):h.update(b);total+=len(b);gz.write(b)
    with gzip.open(o/name,'rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=h.hexdigest():raise ValueError('Compression mismatch')
    report=dict(file=name,sha256=sha(o/name),raw_sha256=h.hexdigest(),raw_bytes=total,sd_source_sha256=sha(a.sd),emmc_source_sha256=sha(a.emmc),os=a.os,payload_verified=True,hardware_install_tested=False)
    (o/'installer.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
