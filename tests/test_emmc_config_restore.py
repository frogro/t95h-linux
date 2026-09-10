import os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Restore(unittest.TestCase):
 def test_contents_modes_and_symlinks(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=p/'source';a.mkdir();(a/'shadow').write_text('test-only');(a/'shadow').chmod(0o600);(a/'link').symlink_to('shadow');b=p/'target';shutil.copytree(a,b,symlinks=True)
   helper=p/'file-metadata';subprocess.run(['cc',str(ROOT/'boards/t95h/emmc-installer/file-metadata.c'),'-o',str(helper)],check=True)
   env=dict(os.environ,T95H_METADATA_CMD=str(helper))
   cmd=['busybox','ash',str(ROOT/'boards/t95h/emmc-installer/check-config'),str(a),str(b)]
   self.assertEqual(subprocess.run(cmd,env=env).returncode,0)
   bad=p/'bad';bad.write_text('#!/bin/sh\nexit 1\n');bad.chmod(0o755)
   self.assertNotEqual(subprocess.run(cmd,env=dict(env,T95H_METADATA_CMD=str(bad))).returncode,0)
   self.assertNotEqual(subprocess.run(cmd,env=dict(env,T95H_METADATA_CMD=str(p/'missing'))).returncode,0)
   (b/'shadow').chmod(0o644);self.assertNotEqual(subprocess.run(cmd,env=env).returncode,0)
   (b/'shadow').chmod(0o600);(b/'shadow').write_text('different');self.assertNotEqual(subprocess.run(cmd,env=env).returncode,0)
 def test_archive_list_excludes_synthetic_parents(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a=p/'source';b=p/'target'
   for x in (a,b):
    (x/'etc').mkdir(parents=True);(x/'etc/passwd').write_text('test-only')
   (a/'etc').chmod(0o700);(b/'etc').chmod(0o755)
   entries=p/'list';entries.write_text('etc/passwd\n')
   helper=p/'metadata';subprocess.run(['cc',str(ROOT/'boards/t95h/emmc-installer/file-metadata.c'),'-o',str(helper)],check=True)
   cmd=['busybox','ash',str(ROOT/'boards/t95h/emmc-installer/check-config'),str(a),str(b),str(entries)]
   env=dict(os.environ,T95H_METADATA_CMD=str(helper))
   self.assertEqual(subprocess.run(cmd,env=env).returncode,0)
   (b/'etc/passwd').chmod(0o600)
   self.assertNotEqual(subprocess.run(cmd,env=env).returncode,0)
 def test_installer_refuses_unattended_input(self):
  r=subprocess.run(['busybox','ash',str(ROOT/'boards/t95h/emmc-installer/t95h-install-emmc')],input='EMMC LOESCHEN\n',capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0)
