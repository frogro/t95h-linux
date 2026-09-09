import hashlib,importlib.util,json,struct,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('console',ROOT/'tools/configure-boot-console.py')
console=importlib.util.module_from_spec(spec);spec.loader.exec_module(console)
class BootRetry(unittest.TestCase):
 def test_binary_source_crc_and_modes(self):
  scripts=ROOT/'boards/t95h/boot/scripts';blob=(scripts/'boot.scm').read_bytes()
  self.assertEqual(hashlib.sha256(blob).hexdigest(),json.loads((scripts/'sha256.json').read_text())['boot.scm'])
  self.assertEqual(blob[72:].decode(),(scripts/'boot.scm.txt').read_text())
  for mode in ['dual','hdmi','uart']:
   b=console.configure(blob,mode);h=bytearray(b[:64]);crc=struct.unpack_from('>I',h,4)[0];struct.pack_into('>I',h,4,0)
   self.assertEqual(zlib.crc32(h),crc);self.assertEqual(zlib.crc32(b[64:]),struct.unpack_from('>I',h,24)[0])
   text=b[72:].decode();self.assertIn('for t95h_sd_try in 1 2 3; do',text)
   self.assertIn('if mmc rescan; then',text);self.assertIn('root=PARTUUID=c5bddd4c-02',text)
   self.assertEqual('console=tty0' in text,mode!='uart');self.assertEqual('console=ttyS0,115200' in text,mode!='hdmi')
  # Exact payload already installed and read back on the test box.
  self.assertEqual(hashlib.sha256(console.configure(blob,'dual')).hexdigest(),'4dfd35ab3766382560594c4a5a6fa50c439a3859505f9091b17b21c56b64b03f')
