import io,tarfile,tempfile,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HOOK=ROOT/'boards/t95h/openwrt/upgrade/platform.sh'
class Media(unittest.TestCase):
 def manifest(self,p,magic):
  data=('\n'.join([magic]+['0'*64]*5+['67108864 2025848832'])+'\n').encode()
  with tarfile.open(p,'w') as t:
   m=tarfile.TarInfo('manifest');m.size=len(data);t.addfile(m,io.BytesIO(data))
 def run_ash(self,code,*args):return subprocess.run(['busybox','ash','-c','. "$1"; shift; '+code,'test',str(HOOK),*map(str,args)],capture_output=True,text=True)
 def test_both_media_and_cross_media_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   for magic,media,other in [('T95H-SD-UPGRADE-1','SD','MMC'),('T95H-EMMC-UPGRADE-1','MMC','SD')]:
    p=Path(d)/'p.tar';self.manifest(p,magic)
    r=self.run_ash('t95h_manifest "$1" && echo "$T95H_MEDIA"',p);self.assertEqual(r.returncode,0);self.assertEqual(r.stdout.strip(),media)
    # Mismatching actual device type must reject before any block read/write.
    r=self.run_ash('t95h_manifest "$1"; cat() { echo "$2"; }; actual="$2"; cat() { echo "$actual"; }; dd() { echo BAD_IO; }; t95h_target_check mmcblk2',p,other)
    self.assertNotEqual(r.returncode,0);self.assertNotIn('BAD_IO',r.stdout)
 def test_unknown_magic_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'p.tar';self.manifest(p,'T95H-WRONG-UPGRADE-1');self.assertNotEqual(self.run_ash('t95h_manifest "$1"',p).returncode,0)
