import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('anotter_publish',ROOT/'tools/anotter/publish.py')
pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)

class PublishTests(unittest.TestCase):
    def fixture(self, root):
        images=[]
        for role in ('sd','emmc','installer'):
            raw=(role+' image').encode();name=role+'.img.gz'
            (root/name).write_bytes(gzip.compress(raw))
            images.append(dict(file=name,sha256=pub.sha(root/name),raw_sha256=hashlib.sha256(raw).hexdigest()))
        images[2].update(os='anotter',payload_verified=True,sd_source_sha256=images[0]['sha256'],emmc_source_sha256=images[1]['sha256'])
        manifest=dict(image=images[0]['file'],sha256=images[0]['sha256'],raw_sha256=images[0]['raw_sha256'],emmc=images[1],sd_emmc_installer=images[2])
        (root/'manifest.json').write_text(json.dumps(manifest))
        (root/'installer.json').write_text(json.dumps(images[2]))
        (root/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['file']+'\n' for x in images))
        return manifest
    def test_complete_pair_and_installer_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            self.assertEqual(len(pub.verify(root)),6)
    def test_corrupt_image_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);(root/'emmc.img.gz').write_bytes(b'broken')
            with self.assertRaisesRegex(ValueError,'Checksum mismatch'):pub.verify(root)
    def test_wrong_installer_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m=self.fixture(root);m['sd_emmc_installer']['emmc_source_sha256']='wrong'
            (root/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'does not match'):pub.verify(root)
