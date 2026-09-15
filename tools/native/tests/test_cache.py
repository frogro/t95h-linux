import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline',ROOT/'pipeline.py')
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copy2(ROOT/'pipeline.py',self.root/'pipeline.py')
        (self.root/'native-common.config').write_text('CONFIG_TEST=y\n')
        (self.root/'overlay').mkdir();(self.root/'overlay'/'board').write_text('board-v1')
    def fingerprint(self,commit='commit',profile='base-A-B',key='public-key'):
        return pipeline.build_fingerprint(self.root,commit,profile,key)
    def test_validation_publishing_and_tests_keep_cache(self):
        before=self.fingerprint()
        p=self.root/'pipeline.py';p.write_text(p.read_text().replace('Incomplete image package selection:', 'Missing image packages:'))
        (self.root/'publisher.py').write_text('new publisher')
        (self.root/'tests').mkdir();(self.root/'tests'/'test_new.py').write_text('new test')
        self.assertEqual(before,self.fingerprint())
    def test_source_profile_signer_and_upstream_are_isolated(self):
        before=self.fingerprint()
        self.assertNotEqual(before,self.fingerprint(profile='base'))
        self.assertNotEqual(before,self.fingerprint(commit='new commit'))
        self.assertNotEqual(before,self.fingerprint(key='new key'))
        (self.root/'overlay'/'board').write_text('board-v2')
        self.assertNotEqual(before,self.fingerprint())
    def test_prepare_logic_change_invalidates_cache(self):
        before=self.fingerprint();p=self.root/'pipeline.py'
        p.write_text(p.read_text().replace("run('make','defconfig',cwd=SOURCE)","run('make','defconfig','NEW=1',cwd=SOURCE)"))
        self.assertNotEqual(before,self.fingerprint())
    def test_feed_patch_change_invalidates_cache(self):
        before=self.fingerprint();p=self.root/'feed-patches'/'video';p.mkdir(parents=True)
        (p/'fix.patch').write_text('new feed patch')
        self.assertNotEqual(before,self.fingerprint())
