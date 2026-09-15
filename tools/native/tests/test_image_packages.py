import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline',ROOT/'pipeline.py')
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)

class ImagePackageTests(unittest.TestCase):
    def test_missing_runtime_plugin_still_rejected_and_named(self):
        with self.assertRaisesRegex(RuntimeError, 'gst1-mod-alsa'):
            pipeline.check_image_packages(['gst1-mod-alsa','kmscube'],'kmscube - 1\n')
    def test_manifest_versions_and_extra_dependencies(self):
        pipeline.check_image_packages(['kmscube'],'kmscube - 1\nlibc - 1\n\n')
    def test_menu_selectors_are_not_runtime_requirements(self):
        groups=json.loads((ROOT/'packages.json').read_text())
        self.assertEqual(set(groups['B_config_only']),{'gstreamer1-plugins-good','gstreamer1-plugins-bad'})
        self.assertFalse(set(groups['B']) & set(groups['B_config_only']))
        for plugin in ['gst1-mod-alsa','gst1-mod-video4linux2','gst1-mod-videoparsersbad','gst1-mod-rtp']:
            self.assertIn(plugin,groups['B'])
