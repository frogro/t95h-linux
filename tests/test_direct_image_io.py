import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('direct_image_io',Path(__file__).resolve().parents[1]/'tools/direct_image_io.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class DirectIO(unittest.TestCase):
 def test_exact_concatenation_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);a=d/'a';b=d/'b';out=d/'out';a.write_bytes(b'A'*4096);b.write_bytes(b'B'*8192)
   report=m.concatenate([a,b],out)
   self.assertEqual(out.read_bytes(),a.read_bytes()+b.read_bytes())
   self.assertEqual(report['sha256'],hashlib.sha256(out.read_bytes()).hexdigest())
   self.assertEqual(report['direct_readback_count'],2)
   with self.assertRaises(FileExistsError):m.concatenate([a,b],out)
 def test_reject_short_input_and_symlink(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);a=d/'a';a.write_bytes(b'bad')
   with self.assertRaises(ValueError):m.concatenate([a],d/'out')
   self.assertFalse((d/'out').exists())
   a.write_bytes(b'A'*4096);link=d/'link';link.symlink_to(a)
   with self.assertRaises(OSError):m.concatenate([link],d/'out')
 def test_mismatch_is_not_success(self):
  with tempfile.TemporaryDirectory() as folder:
   d=Path(folder);a=d/'a';a.write_bytes(b'A'*4096)
   correct=m.digest(a)
   with mock.patch.object(m,'digest',side_effect=[correct,'0'*64,correct]):
    with self.assertRaisesRegex(ValueError,'readback differs'):m.concatenate([a],d/'out')
if __name__=='__main__':unittest.main()
