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
