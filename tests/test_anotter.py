import importlib.util, struct, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('anotter',ROOT/'tools/anotter/build.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class AnotterTest(unittest.TestCase):
    def test_partition_layout_preserves_bootloader(self):
        b=bytearray(b'x'*(4*m.M));b[510:512]=b'\x55\xaa'
        out=m.prefix(b)
        self.assertEqual(out[512:],b[512:])
        start1,size1=struct.unpack('<II',out[454:462]);start2,size2=struct.unpack('<II',out[470:478])
        self.assertEqual(start1,8192);self.assertEqual(start1+size1,start2)
        self.assertEqual((start2+size2)*512,6276*m.M)
    def test_config_keeps_board_and_enables_userspace(self):
        result=m.config('CONFIG_DRM_PANFROST=y\n# CONFIG_USER_NS is not set\nCONFIG_LOCALVERSION="-old"\n')
        self.assertIn('CONFIG_DRM_PANFROST=y',result)
        for symbol in m.REQUIRED:self.assertIn('CONFIG_'+symbol+'=y\n',result)
        self.assertIn('CONFIG_LOCALVERSION="-t95h-anotter-de33"',result)

class KernelProbeTest(unittest.TestCase):
    def test_only_compiler_probes_are_exempt(self):
        spec=importlib.util.spec_from_file_location('kernel_builder',ROOT/'tools/build-profile-kernel.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        self.assertIn('CONFIG_RUSTC_HAS_FILE_AS_C_STR',builder.HOST_PROBES)
        for feature in ['CONFIG_RUST','CONFIG_DRM_PANFROST','CONFIG_USER_NS','CONFIG_EXT4_FS']:
            self.assertNotIn(feature,builder.HOST_PROBES)

class StartupRegressionTests(unittest.TestCase):
    def test_alsa_duplicate_label_and_already_fixed_package(self):
        text='LABEL="alsa_restore_go"\nGOTO="alsa_restore_std"\nLABEL="alsa_restore_go"\nRUN+="restore"\n'
        fixed=m.fix_alsa_restore_rules(text)
        self.assertEqual(fixed.count('LABEL="alsa_restore_go"'),1)
        self.assertEqual(fixed.count('LABEL="alsa_restore_std"'),1)
        self.assertEqual(m.fix_alsa_restore_rules(fixed),fixed)
        with self.assertRaises(ValueError):m.fix_alsa_restore_rules('changed')
    def test_ntp_preserves_servers_and_uses_ifup_lock(self):
        text='[Service]\nExecStart=ntpdate ptbtime2.ptb.de ptbtime3.ptb.de\nRestart=on-failure\n'
        self.assertEqual(m.serialize_ntp_service(text),text.replace('ExecStart=ntpdate','ExecStart=/usr/bin/flock /run/lock/ntpsec-ntpdate /usr/sbin/ntpdate'))
        with self.assertRaises(ValueError):m.serialize_ntp_service('ExecStart=other\n')
    def test_kiosk_service_has_no_libreelec_cpu_dependency(self):
        text=(ROOT/'boards/t95h/anotter/runtime/t95h-hardware.service').read_text()
        self.assertNotIn('cpufreq',text)
        self.assertIn('Before=lightdm.service',text)
        self.assertIn('ExecStart=/usr/lib/t95h/start-hardware',text)
