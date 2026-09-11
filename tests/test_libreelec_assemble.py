import importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('assemble',ROOT/'tools/libreelec/assemble.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ConfigTests(unittest.TestCase):
 def test_retained_config_after_source_cleanup(self):
  with tempfile.TemporaryDirectory() as d:
   le=Path(d);p=le/'build.LibreELEC-T95H.aarch64-test/install_pkg/linux-7.2.3/.image/.config';p.parent.mkdir(parents=True);p.write_text('CONFIG_DRM=y\n')
   self.assertEqual(m.built_kernel_config(le,'7.2.3'),p)
 def test_source_config_and_matching_retained_copy(self):
  with tempfile.TemporaryDirectory() as d:
   le=Path(d);b=le/'build.LibreELEC-T95H.aarch64-test';p=b/'build/linux-7.2.3/.config';p.parent.mkdir(parents=True);p.write_text('CONFIG_DRM=y\n')
   self.assertEqual(m.built_kernel_config(le,'7.2.3'),p)
   q=b/'install_pkg/linux-7.2.3/.image/.config';q.parent.mkdir(parents=True);q.write_bytes(p.read_bytes());self.assertEqual(m.built_kernel_config(le,'7.2.3'),q)
   p.write_text('CONFIG_DRM=n\n')
   with self.assertRaises(ValueError):m.built_kernel_config(le,'7.2.3')
 def test_missing_or_ambiguous_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   le=Path(d)
   with self.assertRaises(ValueError):m.built_kernel_config(le,'7.2.3')
   for suffix in ['a','b']:
    p=le/f'build.LibreELEC-T95H.aarch64-{suffix}/install_pkg/linux-7.2.3/.image/.config';p.parent.mkdir(parents=True);p.write_text('CONFIG_DRM=y\n')
   with self.assertRaises(ValueError):m.built_kernel_config(le,'7.2.3')
