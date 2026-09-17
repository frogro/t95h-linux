import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('di300_prepare', ROOT / 'tools/experimental/di300/prepare.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class StagingSafety(unittest.TestCase):
    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            output.mkdir()
            (output / 'keep').write_text('unchanged')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                module.prepare(Path(tmp) / 'source', output, '7.2')
            self.assertEqual((output / 'keep').read_text(), 'unchanged')

    def test_output_inside_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'outside'):
                module.prepare(tmp, Path(tmp) / 'out', '7.2')

    def test_corrupted_patch_prevents_any_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'manifest.json').write_text('{"series":[{"file":"bad.patch","sha256":"invalid","commit":"test"}]}')
            (root / 'bad.patch').write_text('bad')
            with mock.patch.object(module, 'HERE', root):
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    module.prepare(root / 'source', root / 'out', '7.2')
            self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
