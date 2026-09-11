import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("le_prepare", Path(__file__).resolve().parents[1] / "tools/libreelec/prepare.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class GnuMirrors(unittest.TestCase):
    def test_both_upstream_path_forms(self):
        for scheme in ("http", "https"):
            for prefix in ("", "gnu/"):
                url = f"{scheme}://ftpmirror.gnu.org/{prefix}libidn/libidn2-${{PKG_VERSION}}.tar.gz"
                expected = "https://ftp.gnu.org/gnu/libidn/libidn2-${PKG_VERSION}.tar.gz"
                self.assertEqual(module.gnu_mirror_urls(url), expected)
                self.assertEqual(module.gnu_mirror_urls(expected), expected)

    def test_unrelated_urls_unchanged(self):
        url = "https://example.org/gnu/libidn.tar.gz"
        self.assertEqual(module.gnu_mirror_urls(url), url)

class WireguardArchive(unittest.TestCase):
    def test_pinned_recipe_and_future_version(self):
        recipe = 'PKG_VERSION="1.0.20250521"\nPKG_SHA256="6afe492647c3b0b2f68ab6df524e9e4290d03c34c3027e069e5bbc486949960e"\nPKG_URL="https://git.zx2c4.com/wireguard-tools/snapshot/wireguard-tools-v${PKG_VERSION}.tar.xz"\n'
        fixed = module.wireguard_archive(recipe)
        self.assertIn('sources.openwrt.org', fixed)
        self.assertIn('b6f2628b85b1b23cc06517ec9c74f82d52c4cdbd020f3dd2f00c972a1782950e', fixed)
        self.assertEqual(module.wireguard_archive(fixed), fixed)
        future = recipe.replace('1.0.20250521', '1.0.20260223')
        self.assertEqual(module.wireguard_archive(future), future)
        with self.assertRaises(ValueError):
            module.wireguard_archive(recipe.replace('https://git.zx2c4.com', 'https://example.org'))
