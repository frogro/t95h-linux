import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).resolve().parents[1] / 'tools/audit-openwrt-kmods.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Audit(unittest.TestCase):
    def test_one_provider_symbol_does_not_prove_package(self):
        row = m.assess('kmod-crypto-user', {'Kernel-Config': 'CONFIG_CRYPTO_USER CONFIG_CRYPTO_USER_API_HASH'},
                       {'CONFIG_CRYPTO_USER': 'y', 'CONFIG_CRYPTO_USER_API_HASH': 'n'}, {'crypto-user': 'CRYPTO_USER'})
        self.assertTrue(row['advertised_in_profile'])
        self.assertEqual(row['state'], 'missing_functions')

    def test_removed_symbol_and_expression_need_review(self):
        for req in ['CONFIG_OLD', 'CONFIG_FOO=$(CONFIG_BAR)']:
            self.assertEqual(m.assess('kmod-test', {'Kernel-Config': req}, {}, {})['state'], 'manual_review')

    def test_no_recipe_is_not_success(self):
        self.assertEqual(m.assess('kmod-test', None, {}, {})['state'], 'recipe_unavailable')

    def test_builtin_and_module_without_provider(self):
        for value in ['y', 'm']:
            self.assertEqual(m.assess('kmod-test', {'Kernel-Config': 'CONFIG_FOO'}, {'CONFIG_FOO': value}, {})['state'], 'enabled_without_provider')

    def test_explicit_disabled_option_is_separate(self):
        row = m.assess('kmod-test', {'Kernel-Config': 'CONFIG_FOO CONFIG_BAR=n'}, {'CONFIG_FOO': 'm', 'CONFIG_BAR': 'y'}, {})
        self.assertEqual(row['state'], 'config_conflict_review')
        self.assertEqual(row['missing'], [])

    def test_metadata_blocks_and_unset_config(self):
        data = m.recipes('Package: kmod-first\nKernel-Config: CONFIG_A\n@@\nPackage: kmod-next\nKernel-Config: CONFIG_B\n')
        self.assertEqual(data['kmod-first']['Kernel-Config'], 'CONFIG_A')
        self.assertEqual(m.config('# CONFIG_A is not set\nCONFIG_B=m\n'), {'CONFIG_A':'n','CONFIG_B':'m'})
