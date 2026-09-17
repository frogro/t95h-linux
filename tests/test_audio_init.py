import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class AudioInit(unittest.TestCase):
    def run_init(self, config='', absent=False):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p/'config').write_text(config)
            (p/'amixer').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$AUDIO_LOG"\ncase "$*" in *cget*) exit '+('1' if absent else '0')+';; esac\n')
            (p/'sleep').write_text('#!/bin/sh\nexit 0\n')
            for name in ('amixer', 'sleep'):
                (p/name).chmod(0o755)
            env = dict(os.environ, PATH=str(p)+':/usr/bin:/bin', AUDIO_LOG=str(p/'log'), T95H_AUDIO_CONFIG=str(p/'config'))
            result = subprocess.run(['sh', str(ROOT/'boards/t95h/audio/t95h-audio-init')], env=env, capture_output=True, text=True, timeout=5)
            return result, (p/'log').read_text().splitlines() if (p/'log').exists() else []

    def test_route_mutes_before_enabling_and_respects_volume(self):
        result, calls = self.run_init('LINEOUT_VOLUME=4\nDAC_VOLUME=55\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1], '-q -c Codec cset name=Line Out Playback Switch off,off')
        self.assertIn('-q -c Codec cset name=Line Out Source Playback Route Stereo,Stereo', calls)
        self.assertIn('-q -c Codec cset name=Line Out Playback Volume 4', calls)
        self.assertIn('-q -c Codec cset name=DAC Playback Volume 55', calls)
        self.assertEqual(calls[-1], '-q -c Codec cset name=Line Out Playback Switch on,on')

    def test_missing_codec_has_bounded_retry_and_no_writes(self):
        result, calls = self.run_init(absent=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 30)
        self.assertTrue(all('cget' in line for line in calls))

    def test_disabled_and_invalid_volume_do_not_touch_mixer(self):
        result, calls = self.run_init('ENABLED=0\n')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        for value in ('32', '-1', 'bad'):
            result, calls = self.run_init('LINEOUT_VOLUME='+value+'\n')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(calls, [])
