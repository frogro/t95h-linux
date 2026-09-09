import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Bootstrap(unittest.TestCase):
 def test_existing_checkout_refuses_local_changes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);b=p/'bin';b.mkdir();checkout=p/'checkout';(checkout/'.git').mkdir(parents=True)
   (b/'git').write_text('#!/bin/sh\ncase "$*" in *"remote get-url"*) echo https://github.com/frogro/t95h-linux.git;; *"status --porcelain"*) echo " M README.md";; *) exit 99;; esac\n')
   (b/'gh').write_text('#!/bin/sh\nexit 0\n')
   for f in b.iterdir():f.chmod(0o755)
   env=dict(os.environ,PATH=str(b)+':'+os.environ['PATH'],T95H_INSTALLER_DIR=str(checkout))
   r=subprocess.run(['sh',str(ROOT/'installer.sh'),'dispatch'],env=env,text=True,capture_output=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('Lokale Änderungen',r.stderr)
