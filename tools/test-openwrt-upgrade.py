#!/usr/bin/env python3
"""Exercise actual BusyBox upgrade validation/copy code against regular files only."""
import argparse,hashlib,json,os,subprocess,tarfile,tempfile,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);a=p.parse_args();b=a.build.resolve();proof=json.loads((b/'build-proof.json').read_text());image=b/proof['sysupgrade'];platform=b/'platform.sh'
def run(code,*args,ok=True):
 r=subprocess.run(['busybox','ash','-c','. "$1"; shift; '+code,'test',str(platform),*map(str,args)],capture_output=True,text=True)
 if (r.returncode==0)!=ok:raise RuntimeError(f'Unexpected rc {r.returncode}: {r.stdout} {r.stderr}')
 return r
checks=[]
# procd's synchronous callback must not decompress large root filesystems.
run('gzip() { echo UNEXPECTED_DECOMPRESSION >&2; return 99; }; t95h_target() { return 0; }; platform_check_image "$1"',image)
checks.append('procd_callback_does_not_decompress')
# Exercise the one-pass size/hash validator independently of archive hashes.
with tempfile.TemporaryDirectory(prefix='raw-check-',dir=b) as small:
 dsmall=Path(small); data=b't95h raw stream\n'*4096
 import gzip,io
 archive=dsmall/'raw.tar'
 with tarfile.open(archive,'w') as t:
  payload=gzip.compress(data); m=tarfile.TarInfo('root.gz');m.size=len(payload);t.addfile(m,io.BytesIO(payload))
 digest=hashlib.sha256(data).hexdigest()
 run('t95h_check_raw "$1" root "$2" "$3"',archive,digest,len(data))
 run('t95h_check_raw "$1" root "$2" "$3"',archive,digest,len(data)+1,ok=False)
 run('t95h_check_raw "$1" root "$2" "$3"',archive,'0'*64,len(data),ok=False)
 checks.extend(['one_pass_raw_valid','one_pass_wrong_size_rejected','one_pass_wrong_hash_rejected'])
run('t95h_validate_payload "$1"',image);checks.append('valid_archive_passes_busybox')
# Actual root/boot write and O_DIRECT readback, on expendable regular files.
if True:
 tmp=tempfile.mkdtemp(prefix='upgrade-test-',dir=b)
 d=Path(tmp)
 run('t95h_write_payload "$1" "$2" "$3"',image,d/'root.ext4',d/'boot.fat')
 for file,key in [('root.ext4','rootfs_sha256'),('boot.fat','boot_sha256')]:
  with (d/file).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==proof[key]
 checks.append('real_write_pipeline_and_direct_readback_equal_expected_partitions')
 # A failed root write must never proceed to the boot partition.
 sentinel=d/'boot-sentinel';sentinel.write_bytes(b'unchanged')
 run('t95h_write_payload "$1" "$2" "$3"',image,d/'missing-parent/root',sentinel,ok=False)
 assert sentinel.read_bytes()==b'unchanged'
 checks.append('root_write_failure_aborts_before_boot_write')
 # Exact corruption / missing / extra-member rejection, no output-device calls.
 for mode in ['corrupt','missing','extra']:
  dst=d/(mode+'.tar')
  with tarfile.open(image) as src,tarfile.open(dst,'w') as out:
   for m in src:
    if mode=='missing' and m.name=='boot.gz':continue
    data=src.extractfile(m).read()
    if mode=='corrupt' and m.name=='boot.gz':data=data[:50]+bytes([data[50]^1])+data[51:]
    import io
    out.addfile(m,io.BytesIO(data))
   if mode=='extra':
    m=tarfile.TarInfo('unexpected');m.size=1;out.addfile(m,io.BytesIO(b'x'))
  run('t95h_validate_payload "$1"',dst,ok=False);checks.append(mode+'_archive_rejected')
 # Device checks refuse host/unknown target. Full entry cannot run in a live ext4 root.
 run('t95h_target_check sda',ok=False);checks.append('non_sd_target_rejected')
 run('platform_check_image "$1"',image,ok=False);checks.append('non_t95h_host_rejected')
shutil.rmtree(d)
result={'passed':True,'checks':checks,'hardware_upgrade_tested':False,'config_restore_on_hardware_tested':False,'sysupgrade_sha256':proof['sysupgrade_sha256']}
(b/'upgrade-test.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
