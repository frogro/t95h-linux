# Startup corrections after the dual-console test

Run `tools/stage-startup-fixes.py --profile base-A-B --output build/startup`
to build directly from repository sources; no previous image or parent project
folder is needed. Add `--rootfs PATH` to the newly installed package root to
also stage the ModemManager correction for A. Without it the report explicitly
marks that correction pending. The tested reference DT and external source remain immutable; the tool produces a derivative
DT, the PPU module source for B, and the ModemManager overlay for A.

* All profiles: disable only /i2c-display/display@24. Keep its i2c-gpio parent
  and the userspace FD655 service; the helper requires the bus, not an I2C client.
* B: use the private experimental compatible t95h,h616-prcm-ppu-el3, without
  an upstream fallback compatible. Build the generated ANA module against the
  selected kernel and regenerate /usr/lib/t95h-gpu/SHA256SUMS. Install module
  and DT as one artifact. Original Panfrost is unchanged. The EL3 verification,
  register handling and late-start readiness logic are unchanged. This avoids
  the unsuccessful early upstream PPU probe; it does not claim to repair generic
  H616 secure register access or implement additional hardware power gating.
* A: preserve early add/remove events in the existing ModemManager cache, but
  don't call mmcli before the system D-Bus socket exists. The existing wrapper
  waits for ModemManager and replays the cache. Existing START=60/70 order stays.
  This does not suppress reporting failures after D-Bus becomes available.

Local tests cover semantic DT changes, source match tables, shell syntax and
cached add/remove/replay behavior. Live ModemManager file was installed with
backup and readback; PPU and display need next-boot validation. Do not describe
these derivatives as the previously hardware-tested image.

ext4 requires an offline check of the SD; never run repair on the live rootfs.

Full profile image integration also enables r8152 module autoload for A and
uvcvideo for B. A adds the official r8152-firmware=20260221-r1 package (seven
RTL8153/8156 files). Firmware requests for RTL8157/8159 remain unavailable in
that chosen package and those adapters are not validated. MT7610E is an optional
preferred image in the USB driver; its explicit fallback MT7610U is included.

Set every default ustreamer instance to enabled=0 as well as omitting its rc.d
start link: the package also ships a USB hotplug handler which can start the
service independently of rc.d. This leaves capture/streaming tools available
without enabling a streaming endpoint or attaching Cedrus /dev/video0 by default.
