import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from module_catalog import plan,load

def row(name,objects,deps=(),symbols=None):
 return dict(package=name,state='config_candidate',objects=objects,depends=list(deps),provides=[name+'-any'],symbols=symbols or {'TEST':'m'})
class CatalogTest(unittest.TestCase):
 def test_reference_covers_all_published_packages(self):
  data=load();self.assertEqual(len({r['package'] for r in data['packages']}),976)
 def test_missing_payload_not_advertised_and_dependents_excluded(self):
  data={'retain_objects':[],'packages':[row('kmod-a',['a.ko']),row('kmod-b',['b.ko'],['kmod-a-any'])]}
  result=plan(data,{'CONFIG_TEST':'m'},{'b.ko'},set(),{})
  self.assertEqual(result['packages'],{})
 def test_retained_dependency_never_removed(self):
  data={'retain_objects':['boot.ko'],'packages':[row('kmod-a',['a.ko']),row('kmod-b',['b.ko'])]}
  result=plan(data,{'CONFIG_TEST':'m'},{'boot.ko','a.ko','b.ko'},set(),{'boot.ko':['a.ko']})
  self.assertEqual(result['movable_objects'],['b.ko'])
 def test_shared_files_have_one_owner_with_dependency(self):
  data={'retain_objects':[],'packages':[row('kmod-a',['a.ko']),row('kmod-b',['a.ko','b.ko'])]}
  result=plan(data,{'CONFIG_TEST':'m'},{'a.ko','b.ko'},set(),{'b.ko':['a.ko']})
  self.assertEqual(result['packages']['kmod-a']['owned_objects'],['a.ko'])
  self.assertEqual(result['packages']['kmod-b']['owned_objects'],['b.ko'])
  self.assertIn('kmod-a',result['packages']['kmod-b']['package_dependencies'])
 def test_builtin_has_no_fake_module_payload(self):
  result=plan({'retain_objects':[],'packages':[row('kmod-a',['a.ko'])]}, {'CONFIG_TEST':'y'},set(),{'a.ko'},{})
  self.assertEqual(result['packages']['kmod-a']['owned_objects'],[])
 def test_baseline_loss_fails(self):
  with self.assertRaises(ValueError):plan({'retain_objects':['boot.ko'],'packages':[]},{},set(),set(),{})
 def test_changed_disabled_option_rejected(self):
  result=plan({'retain_objects':[],'packages':[row('kmod-a',[],symbols={'TEST':'n'})]}, {'CONFIG_TEST':'y'},set(),set(),{})
  self.assertEqual(result['packages'],{})
