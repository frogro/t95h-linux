import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('resume', Path(__file__).parents[1] / 'resume-publication.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ManifestTests(unittest.TestCase):
    def test_complete_manifest_and_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d/'image.gz').write_bytes(b'image')
            (d/'SHA256SUMS').write_text(hashlib.sha256(b'image').hexdigest()+'  image.gz\n')
            m.verify_sums(d)
            (d/'image.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                m.verify_sums(d)
    def test_unlisted_and_escaping_files_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d/'extra').write_bytes(b'extra')
            (d/'SHA256SUMS').write_text('')
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                m.verify_sums(d)
            (d/'SHA256SUMS').write_text('abc  ../outside\n')
            with self.assertRaisesRegex(ValueError, 'Invalid'):
                m.verify_sums(d)
