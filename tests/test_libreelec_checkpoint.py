import ast, importlib.util, json, os, shutil, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools/libreelec'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

@unittest.skipUnless(shutil.which('zstd'), 'zstd required for archive round-trip')
class ArchiveTests(unittest.TestCase):
 def test_roundtrip_preserves_toolchain_and_rejects_corruption(self):
  m=load('checkpoint')
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);le=root/'build/libreelec';le.mkdir(parents=True);(root/'build/libreelec-inputs').mkdir();(root/'build/libreelec-request.json').write_text('{}')
   f=le/'compiler';f.write_bytes(b'toolchain');f.chmod(0o755);(le/'cc').symlink_to('compiler');(le/'.stamp').write_text('completed')
   stamp=f.stat().st_mtime_ns;ident={'format':1,'workspace':str(root),'commit':'abc','runner_image':'test','request':{}}
   with patch.object(m,'ROOT',root),patch.object(m,'identity',return_value=ident):
    m.save(root/'checkpoint');shutil.rmtree(le);m.restore(root/'checkpoint')
    self.assertEqual(f.read_bytes(),b'toolchain');self.assertEqual(f.stat().st_mode&0o777,0o755);self.assertTrue((le/'cc').is_symlink());self.assertEqual((le/'.stamp').read_text(),'completed')
    self.assertAlmostEqual(f.stat().st_mtime_ns/1e9,stamp/1e9,delta=1)
    shutil.rmtree(le);a=root/'checkpoint/state.tar.zst';a.write_bytes(a.read_bytes()+b'corrupt')
    with self.assertRaisesRegex(ValueError,'checksum'):m.restore(root/'checkpoint')
    self.assertFalse(le.exists())
 def test_different_source_rejected_before_extract(self):
  m=load('checkpoint')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);a={'format':1,'workspace':str(p),'commit':'old','runner_image':'test','request':{}};(p/'state.json').write_text(json.dumps(a))
   with patch.object(m,'identity',return_value={**a,'commit':'new'}):
    with self.assertRaisesRegex(ValueError,'commit'):m.restore(p)

class SchedulerTests(unittest.TestCase):
 def test_pause_drains_active_packages_and_does_not_mask_failure(self):
  # Exercise the injected queueWork method, without launching upstream's CLI.
  m=load('enable-checkpoint')
  template='class Builder:\n    def queueWork(self):\n        return "normal"\n\nif False:\n    sys.exit(0 if result else 1)\n'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'scripts').mkdir();f=p/'scripts/pkgbuilder.py';f.write_text(template);m.patch(p)
   ns={'os':os,'time':time};exec(compile(ast.Module(body=[ast.parse(f.read_text()).body[0]],type_ignores=[]),str(f),'exec'),ns)
   b=ns['Builder']();marker=p/'paused'
   class Generator:
    active=1;failed=0
    def activeJobCount(self):return self.active
    def failedJobCount(self):return self.failed
   b.generator=Generator()
   with patch.dict(os.environ,T95H_BUILD_DEADLINE='0',T95H_PAUSE_MARKER=str(marker)):
    self.assertTrue(b.queueWork());self.assertFalse(marker.exists())
    b.generator.active=0;b.generator.failed=1;self.assertFalse(b.queueWork());self.assertFalse(marker.exists())
    b.generator.failed=0;self.assertFalse(b.queueWork());self.assertEqual(marker.read_text(),'drained\n');self.assertTrue(b.checkpoint_paused)
