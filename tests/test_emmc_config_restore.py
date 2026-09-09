import os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Restore(unittest.TestCase):
 def test_contents_modes_and_symlinks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=p/'source';a.mkdir();(a/'shadow').write_text('test-only');(a/'shadow').chmod(0o600);(a/'link').symlink_to('shadow');b=p/'target';shutil.copytree(a,b,symlinks=True)
   cmd=['busybox','ash',str(ROOT/'boards/t95h/emmc-installer/check-config'),str(a),str(b)]
   self.assertEqual(subprocess.run(cmd).returncode,0)
   (b/'shadow').chmod(0o644);self.assertNotEqual(subprocess.run(cmd).returncode,0)
   (b/'shadow').chmod(0o600);(b/'shadow').write_text('different');self.assertNotEqual(subprocess.run(cmd).returncode,0)
 def test_installer_refuses_unattended_input(self):
  r=subprocess.run(['busybox','ash',str(ROOT/'boards/t95h/emmc-installer/t95h-install-emmc')],input='EMMC LOESCHEN\n',capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0)
