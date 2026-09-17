import importlib.util,json,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('display',ROOT/'tools/anotter/display.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Display(unittest.TestCase):
 def test_manifest_has_paired_dma_and_scaler_sources(self):
  lock=m.manifest()
  self.assertEqual(set(lock['before']),set(lock['after']))
  self.assertIn('drivers/gpu/drm/sun4i/sun8i_rdma.c',lock['after'])
 def test_reject_changed_source_before_patch(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaisesRegex(ValueError,'source differs'):m.verify(Path(t),'before')
 def test_dtb_moves_only_iommu_property(self):
  with tempfile.TemporaryDirectory() as t:
   t=Path(t);d=t/'tree.dtb';s=t/'tree.dts'
   s.write_text('/dts-v1/; / { soc { bus@1000000 { planes@100000 { test = <123>; }; mixer@280000 { iommus = <88 0>; test = <456>; }; }; }; };')
   subprocess.run(['dtc','-q','-I','dts','-O','dtb','-o',d,s],check=True)
   m.dtb(d)
   def get(node,prop):return subprocess.check_output(['fdtget','-t','u',d,node,prop],text=True).strip()
   self.assertEqual(get('/soc/bus@1000000/planes@100000','iommus'),'88 0')
   self.assertEqual(get('/soc/bus@1000000/planes@100000','test'),'123')
   self.assertEqual(get('/soc/bus@1000000/mixer@280000','test'),'456')
   self.assertNotEqual(subprocess.run(['fdtget',d,'/soc/bus@1000000/mixer@280000','iommus'],capture_output=True).returncode,0)
   with self.assertRaises(Exception):m.dtb(d)

 def test_thermal_changes_only_two_cpu_temperatures(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t)/'board.dtb'
   subprocess.run(['dtc','-q','-I','dts','-O','dtb','-o',d,ROOT/'boards/t95h/dts/t95h-tested-full.dts'],check=True)
   before=d.read_bytes()
   m.thermal(d)
   import libfdt
   dt=libfdt.Fdt(d.read_bytes())
   base='/thermal-zones/cpu-thermal/trips/cpu-trip-'
   for i,temp in enumerate((70000,75000,110000)):
    self.assertEqual(int.from_bytes(dt.getprop(dt.path_offset(base+str(i)),'temperature'),'big'),temp)
   for i,temp in enumerate((60000,70000)):
    dt.setprop(dt.path_offset(base+str(i)),'temperature',temp.to_bytes(4,'big'))
   self.assertEqual(bytes(dt.as_bytearray()),before)
   with self.assertRaisesRegex(ValueError,'Unexpected CPU thermal trip'):m.thermal(d)
