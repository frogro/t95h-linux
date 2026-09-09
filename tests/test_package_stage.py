import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('stage',Path(__file__).resolve().parents[1]/'tools/assemble-openwrt-packages.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
class PackageStageTests(unittest.TestCase):
 def test_reject_foreign_modules(self):
  for name in ('kernel','kmod-usb-core'):
   with self.assertRaises(ValueError):stage.installed_packages('P:t95h-kernel\nV:7.2.3-r8\n\nP:'+name+'\nV:6.12-r1\n')
 def test_require_real_kernel(self):
  with self.assertRaises(ValueError):stage.installed_packages('P:base-files\nV:1\n')
 def test_fixed_release_feeds(self):
  urls=stage.repositories('25.12.5')
  self.assertTrue(all('/25.12.5/' in url and '/kmods/' not in url for url in urls))
  for version in ('snapshot','latest','25.12.5/../../other'):
   with self.assertRaises(ValueError):stage.repositories(version)
