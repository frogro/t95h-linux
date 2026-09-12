import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('contract', ROOT / 'tools/base_module_contract.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class BaseModules(unittest.TestCase):
    def contract(self):
        return {'required_config': {'FOO': 'm', 'BAR': 'm'}, 'providers': {
            'example': {'symbols': ['FOO', 'BAR'], 'objects': {'FOO': ['foo'], 'BAR': ['bar']}}}}

    def test_missing_second_symbol_rejects_provider(self):
        with self.assertRaisesRegex(ValueError, 'BAR'):
            m.verify({'FOO': 'm'}, contract=self.contract())

    def test_missing_payload_rejects_enabled_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'modules.builtin').write_text('')
            (root/'foo.ko').write_bytes(b'fixture')
            with self.assertRaisesRegex(ValueError, 'bar'):
                m.verify({'FOO':'m','BAR':'m'}, root, root/'modules.builtin', self.contract())

    def test_builtin_and_module_are_checked_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'modules.builtin').write_text('kernel/lib/foo.ko\n')
            (root/'bar.ko').write_bytes(b'fixture')
            self.assertEqual(m.verify({'FOO':'y','BAR':'m'}, root, root/'modules.builtin', self.contract()), {'example':'FOO'})
            with self.assertRaisesRegex(ValueError, 'foo'):
                m.verify({'FOO':'m','BAR':'m'}, root, root/'modules.builtin', self.contract())

    def test_all_profiles_keep_router_features_and_board_exclusions(self):
        for path in (ROOT/'boards/t95h/profiles/kconfig-draft').glob('*.config'):
            cfg = m.read_config(path.read_text())
            self.assertIn('crypto-user', m.verify(cfg))
            for symbol in ['PCI', 'BLK_DEV_NVME', 'MHI_BUS']:
                self.assertNotIn(cfg.get(symbol), ('y','m'))

    def test_each_provider_has_payload_contract(self):
        for entry in m.load()['providers'].values():
            self.assertTrue(entry['objects'])
            self.assertTrue(set(entry['objects']) <= set(entry['symbols']))
