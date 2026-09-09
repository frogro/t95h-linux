import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class VifPublication(unittest.TestCase):
 def test_patch_replay_and_order(self):
  board=ROOT/'boards/t95h';lock=json.loads((board/'kernel/source-lock.json').read_text())
  rel='drivers/net/wireless/xradio/sta.c'
  patch=(board/'kernel'/lock['patch']).read_text()
  section=patch.split('+++ b/'+rel+'\n',1)[1].split('\n--- ',1)[0]
  original=''.join(x[1:] for x in section.splitlines(keepends=True) if x.startswith('+'))+'\n'
  entry=next(e for e in lock['files'] if e['path']==rel)
  self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),entry['sha256'])
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/rel;p.parent.mkdir(parents=True);p.write_text(original)
   subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(board/'kernel/incremental/0002-xradio-fix-vif-publication.patch')],cwd=t,check=True,capture_output=True)
   fixed=p.read_text()
   self.assertNotIn('*drv_priv = priv;',fixed)
   self.assertNotIn('struct xradio_vif **drv_priv',fixed)
   self.assertEqual(fixed.count('spin_lock_init(&priv->vif_lock)'),1)
   self.assertLess(fixed.index('spin_lock_init(&priv->vif_lock)'),fixed.index('hw_priv->vif_list[priv->if_id] = vif;'))
