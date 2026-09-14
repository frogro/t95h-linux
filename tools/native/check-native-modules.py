#!/usr/bin/env python3
"""Fail before packaging if a requested native hardware module was omitted."""
from pathlib import Path
import json, re
r=Path(__import__('os').environ['NATIVE_WORK'])
kernels=list((r/'source/build_dir/target-aarch64_cortex-a53_musl/linux-sunxi_cortexa53').glob('linux-*/include/config/kernel.release'))
if len(kernels)!=1:raise SystemExit('Ambiguous kernel build directory')
k=kernels[0].parents[2]
config=(k/'.config').read_text()
required=['VIDEOBUF2_VMALLOC','SOUND','SND','SND_PCM','SND_COMPRESS_OFFLOAD','ARM_ALLWINNER_SUN50I_CPUFREQ_NVMEM','DRM_PANFROST','DRM_SUN4I','DRM_SUN8I_MIXER','DRM_SUN8I_DW_HDMI','VIDEO_SUNXI_CEDRUS','SND_SUN4I_CODEC','SND_SOC_SUNXI_AHUB','IR_SUNXI','BT_HCIBTUSB']
missing=[n for n in required if 'CONFIG_'+n+'=m\n' not in config]
missing += [n for n in ['PM_GENERIC_DOMAINS','PM_GENERIC_DOMAINS_OF','T95H_GUARDED_POWER_DOMAINS'] if 'CONFIG_'+n+'=y\n' not in config]
files=['drivers/media/common/videobuf2/videobuf2-vmalloc.ko']
for name in ['t95h-media','t95h-ir','t95h-compute']:
 text=(r/'source/package/kernel'/name/'Makefile').read_text()
 files+=re.findall(r'\$\(LINUX_DIR\)/([^\s]+\.ko)',text)
builtins={line.removeprefix('kernel/') for line in (k/'modules.builtin').read_text().splitlines()}
missing_files=[f for f in files if f not in builtins and (not (k/f).is_file() or (k/f).stat().st_size==0)]
report={'required_module_symbols':required,'missing_symbols':missing,'checked_kernel_modules':files,'verified_builtins':sorted(set(files)&builtins),'missing_files':missing_files,'passed':not(missing or missing_files)}
(r/'logs/native-module-audit.json').write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']:raise SystemExit('STOP: native module audit failed: '+repr(missing+missing_files))
print('PASS: all requested native hardware modules present')
