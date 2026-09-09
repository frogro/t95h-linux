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

class FourArtifactRelease(Release):
 def stage_four(self,p):
  self.stage(p)
  roles={'sd_install':'sample-install.img','sd_upgrade':'sample-sysupgrade.bin','emmc_upgrade':'sample-emmc-sysupgrade.bin','sd_emmc_installer':'sample-sd-emmc-installer.img.gz'}
  for n in ['sample-emmc-sysupgrade.bin','sample-sd-emmc-installer.img.gz']:(p/n).write_bytes(n.encode())
  with (p/'SHA256SUMS').open('a') as f:
   for n in ['sample-emmc-sysupgrade.bin','sample-sd-emmc-installer.img.gz']:f.write(hashlib.sha256((p/n).read_bytes()).hexdigest()+'  '+n+'\n')
  (p/'release-set.json').write_text(json.dumps(dict(format='T95H-RELEASE-SET-1',artifacts=roles)))
  for media in ['sd','emmc']:(p/(media+'-upgrade-test.json')).write_text(json.dumps(dict(passed=True,sysupgrade_sha256=hashlib.sha256((p/roles[media+'_upgrade']).read_bytes()).hexdigest())))
  (p/'installer-proof.json').write_text(json.dumps(dict(payload_readback_verified=True,sha256=hashlib.sha256((p/roles['sd_emmc_installer']).read_bytes()).hexdigest())))
 def test_all_four_verified(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.stage_four(p);self.assertIn(p/'sample-emmc-sysupgrade.bin',m.assets(p,'base-B','dual'))
 def test_emmc_failure_blocks_publication(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.stage_four(p);(p/'emmc-upgrade-test.json').write_text(json.dumps(dict(passed=False)))
   with self.assertRaises(ValueError):m.assets(p,'base-B','dual')
 def test_missing_installer_role_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.stage_four(p);data=json.loads((p/'release-set.json').read_text());del data['artifacts']['sd_emmc_installer'];(p/'release-set.json').write_text(json.dumps(data))
   with self.assertRaises(ValueError):m.assets(p,'base-B','dual')
