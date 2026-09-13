import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class OfflineStart(unittest.TestCase):
 def test_wlan_without_carrier_or_ssh(self):
  s=(ROOT/'boards/t95h/openwrt/runtime/base/usr/sbin/t95h-wlan-late').read_text()
  loop=s[s.index('n=0'):s.index("logger -t t95h-wlan-late 'Local system/netifd ready")]
  mocks='''ubus() { case "$*" in *'call system board'*) echo '{}';; *'list network.wireless'*) echo network.wireless;; *) return 1;; esac; }
pidof() { return 1; }
logger() { :; }
sleep() { :; }
'''
  self.assertEqual(subprocess.run(['sh','-c',mocks+loop],capture_output=True).returncode,0)
 def test_gpu_ready_offline_but_requires_regulators(self):
  s=(ROOT/'boards/t95h/openwrt/runtime/B/usr/sbin/t95h-gpu-start').read_text()
  ready=s[s.index('ready() {'):s.index('\nif [ "${1:-}"')]
  with tempfile.TemporaryDirectory() as t:
   d=Path(t)
   for i,(name,uv) in enumerate([('t95h-cpu-dcdca',1000000),('t95h-gpu-inherited',960000),('t95h-aldo2-wlan',3300000)]):
    p=d/f'regulator.{i}';p.mkdir();(p/'name').write_text(name);(p/'state').write_text('enabled');(p/'microvolts').write_text(str(uv))
   mocks='''radio_required() { return 1; }
pidof() { return 1; }
ubus() { case "$*" in *'call service list'*) echo worker;; *) return 1;; esac; }
jsonfilter() { case "$*" in *running*) echo false;; *exit_code*) echo 0;; *) return 1;; esac; }
'''
   cmd=mocks+ready.replace('/sys/class/regulator',str(d))+'\nready\n'
   self.assertEqual(subprocess.run(['sh','-c',cmd],capture_output=True).returncode,0)
   (d/'regulator.1/state').write_text('disabled')
   self.assertNotEqual(subprocess.run(['sh','-c',cmd],capture_output=True).returncode,0)
