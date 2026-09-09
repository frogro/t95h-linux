"""Verify independently that only intended DT properties change for each profile."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dt',ROOT/'tools/build-tested-dtb.py')
dt=importlib.util.module_from_spec(spec);spec.loader.exec_module(dt)
spec2=importlib.util.spec_from_file_location('fixes',ROOT/'tools/stage-startup-fixes.py')
fixes=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(fixes)

class ProfileTests(unittest.TestCase):
 def test_all_profile_trees(self):
  reference=json.loads((ROOT/'boards/t95h/dts/expected-tree.json').read_text())
  with tempfile.TemporaryDirectory() as temp:
   for profile in ('base','base-A','base-B','base-A-B'):
    output=Path(temp)/profile
    subprocess.run([sys.executable,str(ROOT/'tools/stage-startup-fixes.py'),'--profile',profile,'--output',str(output)],check=True,capture_output=True)
    actual=dt.inventory(output/'t95h.dtb')
    expected=json.loads(json.dumps(reference))
    expected['nodes']['/i2c-display/display@24']['status']=b'disabled\0'.hex()
    if 'B' in profile:
     expected['nodes']['/soc/power-controller@7010250']['compatible']=b't95h,h616-prcm-ppu-el3\0'.hex()
    else:
     for path in ('/soc/gpu@1800000','/soc/video-codec@1c0e000','/soc/power-controller@7010250'):
      expected['nodes'][path]['status']=b'disabled\0'.hex()
    self.assertEqual(actual,expected,profile)
    self.assertEqual((output/'overlay/etc/modules.d/73-t95h-usb-ethernet').exists(),'A' in profile)
    self.assertEqual((output/'overlay/etc/modules.d/74-t95h-usb-video').exists(),'B' in profile)
    self.assertEqual((output/'ana/t95h_ana_provider.c').exists(),'B' in profile)
 def test_modem_changed_source_refused(self):
  with self.assertRaises(ValueError):fixes.modem_fix('unexpected upstream code')
  with self.assertRaises(ValueError):fixes.modem_fix('\t# Report the event\n'*2)
