#!/usr/bin/env python3
"""Stage bounded startup fixes without altering the tested reference or any device."""
import argparse,hashlib,json,subprocess,importlib.util
from pathlib import Path
import libfdt

def sha(data):return hashlib.sha256(data).hexdigest()
def modem_fix(data):
 old='\t# Report the event\n'
 assert data.count(old)==1
 return data.replace(old,'''	# Events above are cached even before D-Bus exists. The standard wrapper
	# replays that cache after ModemManager becomes available.
	if [ ! -S /var/run/dbus/system_bus_socket ]; then
		mm_log "debug" "D-Bus not ready; event retained in cache"
		return 0
	fi

'''+old)
def main():
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--profile',choices=['base','base-A','base-B','base-A-B'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 P=a.project.resolve();repo=Path(__file__).resolve().parents[1];o=a.output.resolve();o.mkdir(parents=True,exist_ok=False)
 spec=importlib.util.spec_from_file_location('dt',repo/'tools/build-tested-dtb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 src=P/'outputs/profile-audit/integration'/a.profile/'t95h.dtb';before=m.inventory(src);expected=json.loads(json.dumps(before))
 dt=libfdt.Fdt(src.read_bytes());dt.resize(len(src.read_bytes())+1024)
 path='/i2c-display/display@24';dt.setprop_str(dt.path_offset(path),'status','disabled');expected['nodes'][path]['status']=b'disabled\0'.hex()
 hasB='B' in a.profile;hasA='A' in a.profile
 for enabled,name,driver in [(hasA,'73-t95h-usb-ethernet','r8152'),(hasB,'74-t95h-usb-video','uvcvideo')]:
  if enabled:
   dest=o/'overlay/etc/modules.d'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(driver+'\n')
 if hasB:
  path='/soc/power-controller@7010250';val='t95h,h616-prcm-ppu-el3'
  dt.setprop_str(dt.path_offset(path),'compatible',val);expected['nodes'][path]['compatible']=(val+'\0').encode().hex()
  s=repo/'boards/t95h/external/ana/t95h_ana_provider.c';code=s.read_text()
  start=code.index('static const struct of_device_id sun50i_h6_ppu_of_match[] = {');end=code.index('MODULE_DEVICE_TABLE',start)
  code=code[:start]+'''static const struct of_device_id sun50i_h6_ppu_of_match[] = {
	{ .compatible = "t95h,h616-prcm-ppu-el3",
	  .data = &sun50i_h616_ppu_data },
	{ }
};
'''+code[end:]
  (o/'ana').mkdir();(o/'ana/t95h_ana_provider.c').write_text(code);(o/'ana/Makefile').write_text('obj-m := t95h_ana_provider.o\n')
 dt.pack();(o/'t95h.dtb').write_bytes(dt.as_bytearray());assert m.inventory(o/'t95h.dtb')==expected
 if hasA:
  src=P/'outputs/cedrus-hdmi-fixed/A/root/usr/share/ModemManager/modemmanager.common';dest=o/'overlay/usr/share/ModemManager/modemmanager.common';dest.parent.mkdir(parents=True)
  dest.write_text(modem_fix(src.read_text()));subprocess.run(['sh','-n',dest],check=True)
  (o/'modem-source.json').write_text(json.dumps({'source_sha256':sha(src.read_bytes()),'patched_sha256':sha(dest.read_bytes())},indent=2)+'\n')
 report={'profile':a.profile,'hardware_tested':False,'dtb_sha256':sha((o/'t95h.dtb').read_bytes()),'only_expected_dt_changes':True,'display_bus_retained':True,'ana_module_rebuild_required':hasB,'modem_cache_guard':hasA,'kernel_source_changed':False}
 (o/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
