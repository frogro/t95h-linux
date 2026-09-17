import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('le_policy',ROOT/'tools/libreelec/prepare.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class PolicyTests(unittest.TestCase):
 def test_only_passive_cpu_trips_change(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);src=d/'test.dts';dtb=d/'test.dtb'
   src.write_text('/dts-v1/; / { untouched = <123>; thermal-zones { cpu-thermal { trips { cpu-trip-0 { temperature=<60000>; hysteresis=<2000>; }; cpu-trip-1 { temperature=<70000>; }; cpu-trip-2 { temperature=<110000>; }; }; }; }; };')
   subprocess.run(['dtc','-I','dts','-O','dtb','-o',str(dtb),str(src)],check=True)
   result=m.thermal_policy(dtb)
   self.assertEqual(result['cpu_trip_temperatures'],[70000,75000,110000])
   self.assertEqual(subprocess.check_output(['fdtget','-t','u',str(dtb),'/','untouched'],text=True).strip(),'123')
   with self.assertRaises(ValueError):m.thermal_policy(dtb)

 def regulatory(self,failures):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);base=d/'base';runtime=d/'runtime';base.mkdir();bin=d/'bin';bin.mkdir()
   for name in ['regulatory.db','regulatory.db.p7s']:(base/name).write_text('test')
   script=(ROOT/'boards/t95h/libreelec/hardware/prepare-regulatory').read_text().replace('base=/usr/lib/kernel-overlays/base/lib/firmware','base='+str(base)).replace('runtime=/run/kernel-overlays/firmware','runtime='+str(runtime))
   (bin/'iw').write_text('#!/bin/sh\nn=0; [ ! -f "$COUNT" ] || n=$(cat "$COUNT"); n=$((n+1)); echo "$n" > "$COUNT"; [ "$n" -gt "$FAILURES" ]\n')
   (bin/'sleep').write_text('#!/bin/sh\nexit 0\n')
   for p in bin.iterdir():p.chmod(0o755)
   r=subprocess.run(['sh','-c',script],env={**os.environ,'PATH':str(bin)+':/usr/bin:/bin','COUNT':str(d/'count'),'FAILURES':str(failures)},capture_output=True,text=True)
   self.assertTrue((runtime/'regulatory.db').is_file())
   return r.returncode,int((d/'count').read_text())
 def test_regulatory_retries_transient_failure(self):self.assertEqual(self.regulatory(2),(0,3))
 def test_regulatory_does_not_hide_persistent_failure(self):self.assertEqual(self.regulatory(99),(1,15))

class ResolverBootTests(unittest.TestCase):
 def test_missing_optional_pnp_preserves_resolver_without_warning(self):
  self.check_pnp(False)
 def test_present_pnp_keeps_dns_filtering(self):
  self.check_pnp(True)
 def test_changed_upstream_read_is_rejected(self):
  with self.assertRaises(ValueError):m.guard_pnp_resolver('echo changed\n')
 def check_pnp(self,present):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);pnp=d/'pnp';resolver=d/'resolv.conf'
   resolver.write_text('existing\n')
   if present:pnp.write_text('nameserver 0.0.0.0\nnameserver 192.0.2.1\ndomain test\n')
   source="grep '^\\(nameserver\\|domain\\) ' /proc/net/pnp | grep -v '^nameserver 0\\.0\\.0\\.0$' > /etc/resolv.conf\n"
   script=m.guard_pnp_resolver(source).replace('/proc/net/pnp',str(pnp)).replace('/etc/resolv.conf',str(resolver))
   result=subprocess.run(['sh','-c',script],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertEqual(result.stderr,'')
   self.assertEqual(resolver.read_text(),'nameserver 192.0.2.1\ndomain test\n' if present else 'existing\n')

class HardwareStartupTests(unittest.TestCase):
 def test_shorter_timing_keeps_regulator_validation_and_runtime_pm(self):
  text=(ROOT/'boards/t95h/libreelec/hardware/start-hardware').read_text()
  fixed=m.hardware_startup(text)
  self.assertIn('wait_age 30\n',fixed)
  self.assertIn('wait_age 45\n',fixed)
  self.assertNotIn('wait_age 120\n',fixed)
  self.assertIn('existing Panfrost/provider bindings verified',fixed)
  for line in text.splitlines():
   if 'microvolts' in line or '960000' in line or '3300000' in line:
    self.assertIn(line,fixed)
  subprocess.run(['sh','-n'],input=fixed,text=True,check=True)
 def test_changed_startup_contract_is_rejected(self):
  with self.assertRaises(ValueError):m.hardware_startup('new upstream script')
