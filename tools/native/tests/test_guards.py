import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
class PortTests(unittest.TestCase):
    def test_prefixes(self):
        for name, expected in [('prefix.bin','d8fe417be041dd9cd7e1677fed52414fb81f066656a447c2367d9b0fcbc94b75'),('emmc-prefix.bin','589a5fff38e1510524f89afd5691e7a8bac3437c42bcd3dddeaaf3d7ff4f9c78')]:
            data=(ROOT/'overlay/target/linux/sunxi/image/t95h'/name).read_bytes()
            self.assertEqual(len(data),4*1024*1024)
            self.assertEqual(hashlib.sha256(data).hexdigest(),expected)
    def guard(self, medium, prefix, mode):
        patch=(ROOT/'port.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        function=added[added.index('t95h_check_layout() {'):].split('\n}')[0]+'\n}\n'
        with tempfile.TemporaryDirectory() as tmp:
            function=function.replace('/tmp/',tmp+'/')
            script=function+f"""
board_name() {{ echo t95h,h616-tvbox; }}
export_bootdevice() {{ return 0; }}
export_partdevice() {{ eval "$1=fake"; }}
cat() {{ case "$1" in */device/type) echo {medium};; */ro) echo 0;; *) command cat "$@";; esac; }}
get_image() {{ command cat '{ROOT}/overlay/target/linux/sunxi/image/t95h/{prefix}'; }}
get_partitions() {{ printf '1 8192 131072\\n2 139264 3956736\\n' > '{tmp}/partmap.t95h_current'; }}
t95h_check_layout unused {mode}
"""
            return subprocess.run(['sh','-c',script],capture_output=True,text=True)
    def test_quick_validation_checks_both_media(self):
        for medium,prefix in [('SD','prefix.bin'),('MMC','emmc-prefix.bin')]:
            r=self.guard(medium,prefix,'quick');self.assertEqual(r.returncode,0,r.stdout+r.stderr)
    def test_cross_medium_rejected(self):
        self.assertNotEqual(self.guard('SD','emmc-prefix.bin','quick').returncode,0)
        self.assertNotEqual(self.guard('MMC','prefix.bin','quick').returncode,0)
    def test_full_validation_rejects_prefix_only(self):
        r=self.guard('SD','prefix.bin','')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('truncated',r.stdout)
    def test_base_network_packages(self):
        groups=json.loads((ROOT/'packages.json').read_text())
        for name in ['kmod-t95h-xradio','wpad-basic-mbedtls','kmod-wireguard','kmod-crypto-user','kmod-sched-cake']:
            self.assertIn(name,groups['required_base_packages'])
