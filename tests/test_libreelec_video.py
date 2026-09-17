import importlib.util
import os
import subprocess
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('le_video_prepare', Path(__file__).resolve().parents[1] / 'tools/libreelec/prepare.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class VideoRecipeTests(unittest.TestCase):
    def test_t95h_uses_stateless_request_api(self):
        recipe = '''
case "${PROJECT}" in
  Allwinner|Rockchip) PATCHES="deinterlace";;
esac
if [ "${PROJECT}" = "Allwinner" -o "${PROJECT}" = "Rockchip" ]; then
  REQUEST=yes
else
  REQUEST=no
fi
printf '%s:%s' "$REQUEST" "$PATCHES"
'''
        fixed = module.ffmpeg_t95h(recipe)
        for project, expected in [('T95H', 'yes:deinterlace'), ('Allwinner', 'yes:deinterlace'), ('Rockchip', 'yes:deinterlace'), ('Generic', 'no:')]:
            result = subprocess.check_output(['sh', '-c', fixed], env={**os.environ, 'PROJECT': project}, text=True)
            self.assertEqual(result, expected)

    def test_changed_upstream_gate_requires_review(self):
        with self.assertRaises(ValueError):
            module.ffmpeg_t95h('unrecognized recipe')
