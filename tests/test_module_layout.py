import importlib.util, tempfile, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('package_kernel',Path(__file__).resolve().parents[1]/'tools/package-profile-kernel.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ModuleLayout(unittest.TestCase):
 def test_relocation_preserves_dependencies_payload_and_private_provider(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);folder=root/'lib/modules/test';(folder/'kernel/usb').mkdir(parents=True)
   (folder/'kernel/usb/mt76.ko').write_bytes(b'dependency')
   (folder/'kernel/usb/mt76-usb.ko').write_bytes(b'depends=mt76')
   (folder/'t95h_aldo2.ko').write_bytes(b'regulator')
   (folder/'modules.order').write_text('kernel/usb/mt76.ko\nkernel/usb/mt76-usb.ko\nupdates/t95h_ana_provider.ko\n')
   private=root/'usr/lib/t95h-gpu';private.mkdir(parents=True);(private/'t95h_ana_provider.ko').write_bytes(b'late-only')
   m.flatten_modules(root,'test')
   self.assertEqual((folder/'mt76-usb.ko').read_bytes(),b'depends=mt76')
   self.assertEqual((folder/'modules.order').read_text(),'mt76.ko\nmt76-usb.ko\n')
   self.assertFalse((folder/'kernel').exists())
   self.assertEqual((private/'t95h_ana_provider.ko').read_bytes(),b'late-only')
   self.assertFalse((folder/'t95h_ana_provider.ko').exists())
 def test_collision_rejected_before_moves(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);folder=root/'lib/modules/test';(folder/'a').mkdir(parents=True)
   (folder/'a/foo-bar.ko').write_bytes(b'a');(folder/'foo_bar.ko').write_bytes(b'b')
   with self.assertRaises(ValueError):m.flatten_modules(root,'test')
   self.assertTrue((folder/'a/foo-bar.ko').exists())
