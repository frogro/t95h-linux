import hashlib,importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('verify_release',ROOT/'tools/verify_release.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ReleaseDownload(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.names=['test-install.img','test-sysupgrade.bin','platform.sh']
  for name in self.names:(self.root/name).write_bytes(name.encode())
  (self.root/'SHA256SUMS').write_text(''.join(hashlib.sha256(n.encode()).hexdigest()+'  '+n+'\n' for n in self.names))
 def test_pair(self):self.assertEqual(m.verify(self.root),self.names)
 def test_corrupt_download(self):
  (self.root/self.names[0]).write_bytes(b'corrupt')
  with self.assertRaisesRegex(ValueError,'mismatch'):m.verify(self.root)
 def test_missing_update(self):
  (self.root/self.names[1]).unlink()
  with self.assertRaisesRegex(ValueError,'Missing'):m.verify(self.root)
 def test_escape_rejected(self):
  (self.root/'SHA256SUMS').write_text('0'*64+'  ../outside\n')
  with self.assertRaisesRegex(ValueError,'Invalid'):m.verify(self.root)
