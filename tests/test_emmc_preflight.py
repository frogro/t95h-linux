import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('emmc',Path(__file__).resolve().parents[1]/'installer/emmc.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Preflight(unittest.TestCase):
    def sample(self,root_type='SD',extra=''):
        return 'board=t95h,h616-tvbox|allwinner,sun50i-h616|\nroot=mmcblk0p2\ndisk=mmcblk0,'+root_type+',0123456789abcdef0123456789abcdef,769277952\ndisk=mmcblk2,MMC,110100303038473330004aa5b4f184c5,15269888\n'+extra
    def test_sd_root_and_unique_emmc(self):
        r=m.identify(self.sample());self.assertEqual(r['target']['device'],'/dev/mmcblk2');self.assertFalse(r['install_ready'])
    def test_running_from_emmc_rejected(self):
        with self.assertRaises(ValueError):m.identify(self.sample('MMC'))
    def test_ambiguous_target_rejected(self):
        with self.assertRaises(ValueError):m.identify(self.sample(extra='disk=mmcblk3,MMC,0123456789abcdef0123456789abcdef,15269888\n'))
    def test_missing_emmc_rejected(self):
        with self.assertRaises(ValueError):m.identify(self.sample().split('disk=mmcblk2')[0])
if __name__=='__main__':unittest.main()
