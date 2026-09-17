import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

di=load('di300','tools/t95h_di300.py')
inv=load('inventory','tools/build-tested-dtb.py')
emmc=load('emmc_dtb','tools/emmc/prepare-access-dtb.py')

class DeviceTreeTests(unittest.TestCase):
    def test_only_new_node_changes_and_survives_emmc(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sd.dtb'
            subprocess.run(['dtc','-I','dts','-O','dtb','-o',str(path),str(ROOT/'boards/t95h/dts/t95h-tested-full.dts')],check=True,capture_output=True)
            before=inv.inventory(path)
            di.add_dtb(path)
            after=inv.inventory(path)
            delta=after['nodes'].pop(di.NODE)
            self.assertEqual(before,after)
            self.assertEqual(delta['iommus'][-8:],'00000001')
            target=Path(tmp)/'emmc.dtb';emmc.prepare(path,target)
            di.verify_dtb(target)
            self.assertEqual(inv.inventory(target)['nodes'][di.NODE],delta)
            with self.assertRaisesRegex(ValueError,'already present'):
                di.add_dtb(path)

@unittest.skipUnless(shutil.which('mcopy') and shutil.which('mmd'), 'mtools required')
class EmbeddedPayloadTests(unittest.TestCase):
    def test_installer_checks_actual_emmc_payload_and_rejects_old_dtb(self):
        import gzip
        import hashlib
        import struct
        import subprocess
        import sys
        sys.path.insert(0,str(ROOT/'tools'))
        installer=load('installer_di300','tools/build-media-installer.py')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);dtb=base/'board.dtb';fat=base/'boot.fat'
            subprocess.run(['dtc','-I','dts','-O','dtb','-o',str(dtb),str(ROOT/'boards/t95h/dts/t95h-tested-full.dts')],check=True,capture_output=True)
            with fat.open('wb') as stream:stream.truncate(16*1024*1024)
            subprocess.run(['mkfs.vfat',str(fat)],check=True,capture_output=True)
            subprocess.run(['mmd','-i',str(fat),'::/boot'],check=True)
            prefix=bytearray(4*1024*1024);prefix[510:512]=b'\x55\xaa'
            struct.pack_into('<II',prefix,454,8192,fat.stat().st_size//512)
            for present in (False,True):
                if present:di.add_dtb(dtb)
                subprocess.run(['mcopy','-o','-i',str(fat),str(dtb),'::/boot/t95h.dtb'],check=True)
                raw=bytes(prefix)+fat.read_bytes();image=base/'image.gz'
                with gzip.open(image,'wb') as stream:stream.write(raw)
                output=base/str(present);output.mkdir()
                if present:
                    self.assertEqual(installer.inspect_emmc_boot(image,output),(len(raw),hashlib.sha256(raw).hexdigest()))
                else:
                    import libfdt
                    with self.assertRaises(libfdt.FdtException):installer.inspect_emmc_boot(image,output)
