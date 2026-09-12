import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('feed',Path(__file__).resolve().parents[1]/'tools/module_feed.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Feed(unittest.TestCase):
    def test_fixed_release_url_only(self):
        url='https://github.com/frogro/t95h-linux/releases/download/t95h-feedtest-123-1'
        self.assertEqual(m.validate_url(url),url)
        for invalid in [url.replace('https:','http:'),url.replace('t95h-feedtest-123-1','latest'),url+'?x=1']:
            with self.assertRaises(ValueError):m.validate_url(invalid)

    def test_no_split_when_another_module_depends_on_leaf(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';folder=root/'lib/modules/7.2.3';folder.mkdir(parents=True)
            (folder/'modules.dep').write_text('other.ko: veth.ko\nveth.ko:\n')
            with self.assertRaisesRegex(ValueError,'not a leaf'):
                m.split(root,'7.2.3',Path(d)/'feed',{},'7.2.3-r1','0~abc',
                    'https://github.com/frogro/t95h-linux/releases/download/t95h-feedtest-123-1',
                    None,None,None,None,0,{})

    def test_missing_module_is_not_advertised(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';folder=root/'lib/modules/7.2.3';folder.mkdir(parents=True)
            (folder/'modules.dep').write_text('')
            with self.assertRaisesRegex(ValueError,'Missing selected module'):
                m.split(root,'7.2.3',Path(d)/'feed',{'veth':'VETH'},'7.2.3-r1','0~abc',
                    'https://github.com/frogro/t95h-linux/releases/download/t95h-feedtest-123-1',
                    None,None,None,None,0,{})
