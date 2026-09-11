import importlib.util,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('media',ROOT/'tools/build-media-installer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Layout(unittest.TestCase):
 def prefix(self):
  p=bytearray(4*m.M);p[510:512]=b'\x55\xaa'
  struct.pack_into('<II',p,470,8192,8192)
  return p
 def test_appends_without_altering_bootloader_or_existing_partitions(self):
  p=self.prefix();p[8192:8200]=b'bootcode'
  q=m.append_partition(p,8*m.M,128*m.M)
  self.assertEqual(q[:478],p[:478]);self.assertEqual(q[494:],p[494:])
  self.assertEqual(m.partition(q,2),(16384,262144))
 def test_refuses_existing_third_partition_or_truncated_sd(self):
  p=self.prefix();p[478]=1
  with self.assertRaises(ValueError):m.append_partition(p,8*m.M,128*m.M)
  with self.assertRaises(ValueError):m.append_partition(self.prefix(),9*m.M,128*m.M)
 def test_refuses_noninteractive_install_before_any_device_access(self):
  result=subprocess.run(['bash',str(ROOT/'boards/t95h/media-installer/install-emmc.sh')],stdin=subprocess.DEVNULL,capture_output=True,text=True)
  self.assertNotEqual(result.returncode,0)
  self.assertIn('STOP:',result.stderr)
