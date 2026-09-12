import importlib.util, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools/libreelec'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class FirmwareTests(unittest.TestCase):
 def test_install_leaves_firmware_symlink_destination_free(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);src=p/'pkg';build=p/'build';out=p/'install'
   (src/'firmware/xr819').mkdir(parents=True);(src/'system.d').mkdir();build.mkdir()
   for name in ['t95h.dtb','cpufreq.conf','grow-emmc-storage','system.d/t95h-grow-emmc.service','start-hardware','prepare-regulatory','kodi.conf','system.d/test.service','firmware/xr819/fw.bin']:(src/name).write_text(name)
   for name in ['t95h_aldo2.ko','t95h_ana_provider.ko']:(build/name).write_text(name)
   subprocess.run(['bash','-eu','-c','source "$1"; get_full_firmware_dir() { echo usr/lib/kernel-overlays/base/lib/firmware; }; makeinstall_target','test',str(ROOT/'boards/t95h/libreelec/hardware/package.mk')],env={'PATH':'/usr/bin:/bin','PKG_DIR':str(src),'PKG_BUILD':str(build),'INSTALL':str(out)},check=True)
   self.assertFalse((out/'usr/lib/firmware').exists())
   self.assertEqual((out/'usr/lib/kernel-overlays/base/lib/firmware/xr819/fw.bin').read_text(),'firmware/xr819/fw.bin')
   (out/'usr/lib/firmware').symlink_to('/run/kernel-overlays/firmware')
 def test_migration_rejects_kernel_changes(self):
  m=load('checkpoint');old='eddc4db5d27c90788c064c7a028ef76b8f1fcf16'
  with patch.object(m.subprocess,'check_output',return_value='boards/t95h/libreelec/hardware/package.mk\n'):self.assertTrue(m.packaging_only_migration(old,'new'))
  with patch.object(m.subprocess,'check_output',return_value='boards/t95h/kernel/tested-kernel-source.patch\n'):self.assertFalse(m.packaging_only_migration(old,'new'))
  self.assertFalse(m.packaging_only_migration('unreviewed','new'))
 def test_refresh_keeps_other_packages(self):
  m=load('refresh-firmware-package');new=(ROOT/'boards/t95h/libreelec/hardware/package.mk').read_text()
  old=new.replace('  local firmware_dir="${INSTALL}/$(get_full_firmware_dir)"\n','').replace('"${firmware_dir}"','${INSTALL}/usr/lib/firmware').replace('"${firmware_dir}/"','${INSTALL}/usr/lib/firmware/')
  with tempfile.TemporaryDirectory() as d:
   le=Path(d);recipe=le/'projects/T95H/packages/t95h-hardware/package.mk';recipe.parent.mkdir(parents=True);recipe.write_text(old)
   b=le/'build.LibreELEC-T95H.aarch64-test/build';(b/'t95h-hardware-1').mkdir(parents=True);(b/'linux-7.2.3').mkdir();(b/'linux-7.2.3/keep').write_text('object')
   m.refresh(le);self.assertFalse((b/'t95h-hardware-1').exists());self.assertTrue((b/'linux-7.2.3/keep').exists());self.assertEqual(recipe.read_text(),new)
