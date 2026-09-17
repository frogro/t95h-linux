import importlib.util, os, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class WlanStart(unittest.TestCase):
 def execute(self,ssid='',external=False,interface=True):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);boot=d/'boot';boot.mkdir();bin=d/'bin';bin.mkdir()
   if external:(boot/'wpa_supplicant.conf').write_text('network={}\n')
   iface=d/'wlan0'
   if interface:iface.mkdir()
   config=d/'wpa_supplicant.conf'
   for name,body in {'get-ini':'echo "$TEST_SSID"','kiosk-wifi':'echo generator >> "$CALLS"; echo network={} > "$CONFIG"','rfkill':'echo "rfkill $*" >> "$CALLS"','iw':'echo "iw $*" >> "$CALLS"','ifup':'echo "ifup $*" >> "$CALLS"','sleep':':'}.items():
    p=bin/name;p.write_text('#!/bin/sh\n'+body+'\n');p.chmod(0o755)
   script=(ROOT/'boards/t95h/anotter/runtime/start-wlan').read_text().replace('boot=/boot/firmware','boot='+str(boot)).replace('/usr/bin/kiosk-wifi',str(bin/'kiosk-wifi')).replace('/tmp/wpa_supplicant.conf',str(config)).replace('/sys/class/net/wlan0',str(iface))
   r=subprocess.run(['bash','-c',script],env={**os.environ,'PATH':str(bin)+':/usr/bin:/bin','TEST_SSID':ssid,'CALLS':str(d/'calls'),'CONFIG':str(config)},capture_output=True,text=True,timeout=5)
   return r,(d/'calls').read_text() if (d/'calls').exists() else ''
 def test_empty_configuration_keeps_ethernet_and_dns_untouched(self):
  r,calls=self.execute();self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(calls,'')
 def test_ini_and_external_configuration_start_wlan_only(self):
  for kw in [{'ssid':'Example'},{'external':True}]:
   r,calls=self.execute(**kw);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('generator\n',calls);self.assertIn('ifup wlan0\n',calls);self.assertNotIn('eth0',calls)
 def test_missing_interface_stops_without_ifup(self):
  r,calls=self.execute(ssid='Example',interface=False);self.assertNotEqual(r.returncode,0);self.assertNotIn('ifup',calls)
 def test_emmc_conversion_preserves_wlan_node(self):
  spec=importlib.util.spec_from_file_location('emmc_access',ROOT/'tools/emmc/prepare-access-dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);src=d/'a.dts';dtb=d/'a.dtb';out=d/'b.dtb'
   src.write_text('/dts-v1/; / { soc { mmc@4021000 { status="okay"; }; mmc@4022000 { compatible="allwinner,sun50i-h616-emmc"; status="disabled"; }; }; };')
   subprocess.run(['dtc','-q','-I','dts','-O','dtb','-o',str(dtb),str(src)],check=True)
   m.prepare(dtb,out)
   self.assertEqual(subprocess.check_output(['fdtget','-t','s',str(out),'/soc/mmc@4021000','status'],text=True).strip(),'okay')
