import hashlib, importlib.util, json, struct, subprocess, tempfile, unittest, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
update=load('boot_update','tools/boot/update.py')
prepare=load('corrected','tools/emmc/prepare-corrected-prefix.py')
class BootUpdateTests(unittest.TestCase):
 def test_only_spl_changes_and_wrong_medium_rejected(self):
  for medium,name in [('sd','prefix.bin'),('emmc','emmc-prefix.bin')]:
   raw=bytearray((ROOT/'tools/native/overlay/target/linux/sunxi/image/t95h'/name).read_bytes())
   oldspl=ROOT/('boards/t95h/boot/pmic305/legacy-sd.toc0' if medium=='sd' else 'boards/t95h/boot/emmc/spl-reset-fifo.toc0')
   raw[8192:49152]=oldspl.read_bytes();raw=bytes(raw)
   new=update.corrected_prefix(raw,medium)
   self.assertEqual(new[:8192],raw[:8192]);self.assertEqual(new[49152:],raw[49152:])
   self.assertNotEqual(new[8192:49152],raw[8192:49152])
   self.assertEqual(update.corrected_prefix(new,medium),new)
   with self.assertRaises(ValueError):update.corrected_prefix(raw,'sd' if medium=='emmc' else 'emmc')
   changed=bytearray(raw);changed[50000]^=1
   with self.assertRaises(ValueError):update.corrected_prefix(changed,medium)
   # Combined images and resized partitions may change only the first sector.
   changed=bytearray(raw);changed[478:494]=bytes(range(16))
   self.assertEqual(update.corrected_prefix(changed,medium)[:512],changed[:512])
 def test_legacy_derivation_matches_native_assets(self):
  raw=bytearray((ROOT/'tools/native/overlay/target/linux/sunxi/image/t95h/prefix.bin').read_bytes())
  raw[8192:49152]=(ROOT/'boards/t95h/boot/pmic305/legacy-sd.toc0').read_bytes()
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'old';src.write_bytes(raw)
   for medium,name in [('sd','prefix.bin'),('emmc','emmc-prefix.bin')]:
    dest=d/medium;prepare.prepare(src,dest,medium)
    self.assertEqual(dest.read_bytes(),(ROOT/'tools/native/overlay/target/linux/sunxi/image/t95h'/name).read_bytes())
 def test_boot_script_cleanup_preserves_arguments_and_checks_crc(self):
  blob=(ROOT/'boards/t95h/boot/scripts/boot.scm').read_bytes()
  # Existing historical kernel7 diagnostic init must not be migrated by this tool.
  with self.assertRaises(ValueError):update.clean_script(blob)
  text=(ROOT/'tools/native/overlay/target/linux/sunxi/image/t95h/boot.cmd').read_text().replace('false\n','while true; do sleep 60; done\n')
  payload=struct.pack('>II',len(text.encode()),0)+text.encode()
  h=bytearray(blob[:64]);struct.pack_into('>I',h,4,0);struct.pack_into('>I',h,12,len(payload));struct.pack_into('>I',h,24,zlib.crc32(payload));struct.pack_into('>I',h,4,zlib.crc32(h))
  old=bytes(h)+payload;new=update.clean_script(old)
  self.assertNotIn(b'while true',new);self.assertIn(b'root=PARTUUID=c5bddd4c-02',new)
  self.assertEqual(update.clean_script(new),new)
  with self.assertRaises(ValueError):update.clean_script(old[:-1]+b'x')
