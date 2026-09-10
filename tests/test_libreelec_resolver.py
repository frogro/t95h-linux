import importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('resolvele',Path(__file__).resolve().parents[1]/'tools/libreelec/resolve.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Resolve(unittest.TestCase):
 def test_stable_annotated_tag(self):
  values=[{'tag_name':'12.2.1','draft':False,'prerelease':False,'html_url':'https://example.test/release'}, {'object':{'type':'tag','sha':'a'*40}}, {'object':{'type':'commit','sha':'b'*40}}]
  with patch.object(m.subprocess,'check_output',side_effect=[json.dumps(x) for x in values]):
   r=m.resolve();self.assertEqual(r['commit'],'b'*40);self.assertEqual(r['tag'],'12.2.1')
 def test_prerelease_no_fallback(self):
  with patch.object(m.subprocess,'check_output',return_value=json.dumps({'tag_name':'13.0.0','prerelease':True,'draft':False})) as call:
   with self.assertRaises(ValueError):m.resolve()
   self.assertEqual(call.call_count,1)
 def test_network_failure_no_fallback(self):
  with patch.object(m.subprocess,'check_output',side_effect=RuntimeError('offline')):
   with self.assertRaises(RuntimeError):m.resolve()
