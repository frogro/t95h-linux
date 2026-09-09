import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class RadioPolicy(unittest.TestCase):
 def test_configured_radio_requirement(self):
  source=(ROOT/'boards/t95h/openwrt/runtime/B/usr/sbin/t95h-gpu-start').read_text()
  function=source[source.index('radio_required() {'):source.index('\nready() {')]
  for radio,ifaces,expected in [('0',[('radio0','0')],0),('0',[('radio0','1')],1),('1',[('radio0','0')],1),('0',[],1),('0',[('radio1','0')],1),('0',[('radio0','1'),('radio0','0')],0)]:
   with self.subTest(radio=radio,ifaces=ifaces),tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'functions.sh'
    stub='config_load() { return 0; }\nconfig_get() {\n case "$2:$3" in\n'
    stub+=' radio0:disabled) eval "$1='+radio+'" ;;\n'
    for i,(device,disabled) in enumerate(ifaces):
     stub+=f' iface{i}:device) eval "$1={device}" ;;\n iface{i}:disabled) eval "$1={disabled}" ;;\n'
    stub+=' *) return 1 ;;\n esac\n}\nconfig_foreach() {\n'
    for i in range(len(ifaces)):stub+=f' "$1" iface{i}\n'
    stub+=' :\n}\n';p.write_text(stub)
    command=function.replace('. /lib/functions.sh','. '+str(p))+'\nradio_required\n'
    result=subprocess.run(['sh','-c',command],capture_output=True,text=True)
    self.assertEqual(result.returncode,expected,result.stderr)
if __name__=='__main__':unittest.main()
