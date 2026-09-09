import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('publish',Path(__file__).resolve().parents[1]/'tools/publish-release.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Release(unittest.TestCase):
 def stage(self,p):
  files={'sample-install.img':b'install','sample-sysupgrade.bin':b'upgrade','platform.sh':b'hook'}
  for name,data in files.items():(p/name).write_bytes(data)
  (p/'SHA256SUMS').write_text(''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in files.items()))
  (p/'request.json').write_text(json.dumps(dict(profile='base-B',console='dual')))
  (p/'upgrade-test.json').write_text(json.dumps(dict(passed=True,sysupgrade_sha256=hashlib.sha256(b'upgrade').hexdigest())))
  (p/'RELEASE-NOTES.md').write_text('Experimental')
  (p/'t95h-keep').write_text('/etc/')
 def test_matching_payload_and_profile(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.stage(p);self.assertIn(p/'sample-install.img',m.assets(p,'base-B','dual'))
 def test_wrong_profile_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.stage(p)
   with self.assertRaises(ValueError):m.assets(p,'base-A','dual')
 def test_stale_test_report_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.stage(p);(p/'upgrade-test.json').write_text(json.dumps(dict(passed=True,sysupgrade_sha256='0'*64)))
   with self.assertRaises(ValueError):m.assets(p,'base-B','dual')
 def test_failed_checks_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.stage(p);(p/'upgrade-test.json').write_text(json.dumps(dict(passed=False)))
   with self.assertRaises(ValueError):m.assets(p,'base-B','dual')
