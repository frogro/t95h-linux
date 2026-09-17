import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('anotter_update', ROOT/'tools/anotter/update-sd.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class Update(unittest.TestCase):
    def test_layout_rejects_emmc_and_other_systems(self):
        header = bytearray(512)
        header[510:] = b'\x55\xaa'
        struct.pack_into('<II', header, 454, 8192, 262144)
        for disk_id in (0, 0xa0950002):
            struct.pack_into('<I', header, 440, disk_id)
            with self.assertRaises(ValueError):
                u.sd_layout(header)
        struct.pack_into('<I', header, 440, 0xa0950001)
        self.assertEqual(u.sd_layout(header), (4*u.M, 128*u.M))
        struct.pack_into('<I', header, 454, 2048)
        with self.assertRaises(ValueError):
            u.sd_layout(header)

    def test_manifest_accepts_both_sd_variants_not_emmc(self):
        manifest = dict(image='solo.img.gz', sha256='one', raw_sha256='two',
                        sd_emmc_installer=dict(file='combined.img.gz', sha256='three', raw_sha256='four'))
        self.assertEqual(u.image_entry(manifest, 'solo.img.gz')['sha256'], 'one')
        self.assertEqual(u.image_entry(manifest, 'combined.img.gz')['raw_sha256'], 'four')
        with self.assertRaises(ValueError):
            u.image_entry(manifest, 'emmc.img.gz')

    @unittest.skipUnless(shutil.which('mcopy') and shutil.which('mkfs.vfat'), 'FAT integration tools missing')
    def test_real_fat_roundtrip_preserves_settings_but_replaces_boot_files(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            source = d/'source'; source.mkdir()
            (source/'boot').mkdir()
            (source/'www-public').mkdir()
            for name, data in {'kioskbrowser.ini':'url=personal', 'wpa_supplicant.conf':'network=private',
                               'authorized_keys':'public-test-key', 'ssh_host_ed25519_key':'test-only',
                               'www-public/index.html':'personal page', 'boot/boot.scm':'OLD boot',
                               'Image':'OLD kernel'}.items():
                (source/name).write_text(data)
            def fat(name):
                p = d/name
                with p.open('wb') as f: f.truncate(128*u.M)
                subprocess.run(['mkfs.vfat', str(p)], check=True, capture_output=True)
                return p
            old = fat('old.fat')
            for p in source.iterdir():
                u.run('mcopy', '-s', '-i', old, p, '::/')
            saved = d/'settings'
            hashes = u.snapshot(old, saved, d/'extracted')
            self.assertNotIn('Image', hashes)
            self.assertNotIn('boot/boot.scm', hashes)
            (saved/'settings-sha256.json').write_text(json.dumps(hashes))
            new = fat('new.fat')
            (source/'boot/boot.scm').write_text('NEW boot')
            (source/'Image').write_text('NEW kernel')
            (source/'kioskbrowser.ini').write_text('defaults')
            for p in (source/'boot', source/'Image', source/'kioskbrowser.ini'):
                u.run('mcopy', '-s', '-i', new, p, '::/')
            u.restore(new, saved, d/'verified')
            self.assertEqual((d/'verified/kioskbrowser.ini').read_text(), 'url=personal')
            self.assertEqual((d/'verified/boot/boot.scm').read_text(), 'NEW boot')
            self.assertEqual((d/'verified/Image').read_text(), 'NEW kernel')
            self.assertEqual((d/'verified/www-public/index.html').read_text(), 'personal page')
            self.assertFalse((d/'verified/settings-sha256.json').exists())

    def test_emmc_update_selects_existing_emmc_not_rescue_sd(self):
        # Execute the real pre-confirmation branch with mocked mount/device-read only.
        script = (ROOT/'boards/t95h/media-installer/install-emmc.sh').read_text()
        block = script.split('if [ "$mode" = --update ]; then', 1)[1].split("printf 'Zum Bestätigen", 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory); (d/'old/boot').mkdir(parents=True)
            (d/'old/kioskbrowser.ini').write_text('existing eMMC settings')
            (d/'old/boot/boot.scm').write_text('boot')
            setup = '''set -eu
fail() { exit 42; }
mount() { :; }
od() { echo '02 00 95 a0'; }
work=$1; mode=$2; disk=mmcblk9; boot=/rescue-sd
'''
            for mode, expected in [('--update', str(d/'old')), ('install', '/rescue-sd')]:
                result = subprocess.run(['bash', '-c', setup+'if [ "$mode" = --update ]; then'+block+'\necho "SOURCE=$boot"', 'test', str(d), mode], check=True, capture_output=True, text=True)
                self.assertIn('SOURCE='+expected, result.stdout)
            (d/'old/kioskbrowser.ini').unlink()
            result = subprocess.run(['bash','-c',setup+'if [ "$mode" = --update ]; then'+block,'test',str(d),'--update'],capture_output=True)
            self.assertEqual(result.returncode, 42)
