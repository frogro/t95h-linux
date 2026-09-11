#!/usr/bin/env python3
"""Refresh only the T95H package after an approved checkpoint migration."""
import shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def refresh(le):
 recipe=le/'projects/T95H/packages/t95h-hardware/package.mk'
 new=ROOT/'boards/t95h/libreelec/hardware/package.mk'
 if recipe.read_bytes()==new.read_bytes():return
 old=recipe.read_text()
 expected=new.read_text().replace('  local firmware_dir="${INSTALL}/$(get_full_firmware_dir)"\n','').replace('"${firmware_dir}"','${INSTALL}/usr/lib/firmware').replace('"${firmware_dir}/"','${INSTALL}/usr/lib/firmware/')
 if old!=expected:raise ValueError('Unexpected old hardware recipe; no cleanup performed')
 shutil.copyfile(new,recipe)
 # Invalidate this package only. The image script creates a fresh system tree.
 for build in le.glob('build.LibreELEC-T95H.aarch64-*'):
  for package in build.glob('build/t95h-hardware-*'):
   shutil.rmtree(package)
  for stamp in build.glob('**/.stamps/t95h-hardware'):
   if stamp.is_dir():shutil.rmtree(stamp)
   else:stamp.unlink()
 print('T95H firmware recipe refreshed; all other compiled packages retained')
if __name__=='__main__':refresh(Path(sys.argv[1]).resolve())
