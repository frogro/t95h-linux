import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'overlay/package/utils/t95h-board/files/etc/uci-defaults/97-t95h-wlan-defaults'
class Migration(unittest.TestCase):
 def run_migration(self,ssid,mode='ap',device='radio0'):
  text=SCRIPT.read_text().replace('. /lib/functions.sh','')
  pre='''cat() { echo t95h,h616-tvbox; }
config_load() { :; }
config_foreach() { migrate_test_ap restored; }
uci() { printf '%s\\n' "$*"; }
'''+f'''config_get() {{ case "$3" in mode) v='{mode}';; ssid) v='{ssid}';; device) v='{device}';; esac; eval "$1=\\\"$v\\\""; }}\n'''
  r=subprocess.run(['sh'],input=pre+text,text=True,capture_output=True,check=True)
  return r.stdout
 def test_migrate_restored_test_ap(self):
  s=self.run_migration('T95H-Test');self.assertIn('ssid=OpenWrt',s);self.assertIn('key=openwrtopenwrt',s)
 def test_preserve_custom_ap_station_and_other_radio(self):
  for ssid,mode,device in [('MyNetwork','ap','radio0'),('T95H-Test','sta','radio0'),('T95H-Test','ap','radio1')]:
   self.assertNotIn('set ',self.run_migration(ssid,mode,device))
