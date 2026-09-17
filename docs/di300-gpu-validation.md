# DI300 and GPU startup qualification — 2026-09-17

## Pinned upstream work

Jernej Škrabec's [h616-deinterlace-v1](https://github.com/jernejsk/linux-1/tree/h616-deinterlace-v1)
contains an H616 DI300 driver, not merely the older H6 deinterlacer.
The eleven selected commits end at
[b4cc0dbd13ce79c1a5bc98a949d8920a59b6a0df](https://github.com/jernejsk/linux-1/commit/b4cc0dbd13ce79c1a5bc98a949d8920a59b6a0df).
They include follow-up buffer, FMD and Request API fixes. Unrelated display
changes at the branch head are deliberately excluded. Original patches,
authorship and SHA-256 hashes are retained in `tools/experimental/di300/`.
No release build currently invokes this experimental directory.

`prepare.py --source KERNEL --output NEW_DIRECTORY --kernel-api 7.2`
verifies hashes and replays patches with zero fuzz into a separate review
overlay. It does not modify the source, enable a config, install a DTB or
load a module. Existing output is rejected. For 6.12 driver review, use
`--kernel-api 6.12 --driver-only`.

## What passed, and what did not

* 7.2.3: all eleven patches replayed with zero fuzz; external module compilation,
  modpost and link succeeded against the prepared Anotter kernel.
* 6.12.94: driver object compilation succeeded after the explicit compatibility
  patch (metadata helper, file handle API and allocation API). The prepared
  tree lacks Module.symvers: full modpost/module ABI validation remains open.
* 6.12 DT: the unmodified upstream DT patch fails against the local baseline,
  which lacks the expected GPU context. OpenWrt supplies board multimedia
  nodes through its own overlays. `--driver-only` explicitly excludes DT;
  it is not evidence of complete OpenWrt integration.
* No DI300 module has been loaded on the box. An Anotter-built module must not
  be loaded into LibreELEC merely because the kernel version number matches.

The node requires MMIO 0x01420000/0x40000, IRQ 89, the deinterlace bus/module
clocks and reset, and IOMMU master **1**. Preserve these upstream definitions;
do not copy display master 0. Check the effective DTB and its IOMMU phandle,
not just a source fragment. CONFIG_VIDEO_SUN50I_DI300=m also requires the
V4L2 M2M, DMA-contiguous buffer, clock and PM dependencies.

## Qualification before enabling release images

1. Build with the exact target kernel config and Module.symvers; compile the
   effective board DTB and validate bindings. Review DMA/IOMMU and abort,
   STREAMOFF, IRQ completion and error cleanup before runtime activation.
2. First test from removable SD with a known-good boot image and bounded test
   processes. Confirm DI300 identifies separately from Cedrus; enumerate raw
   input/output formats and field handling. Never select a fixed video number.
3. Feed known interlaced material; check progressive output, frame/field order,
   buffer completion, IRQ counters and absence of IOMMU faults. Exercise
   repeated open/close, STREAMOFF and interrupted playback. Measure CPU and
   stability under playback load; compilation alone is not acceptance.
4. Re-enable the LibreELEC FFmpeg V4L2 deinterlace filter only with a usable
   DI300 device. Kodi's FilterTest is a capability probe: the current Cedrus
   decoder accepts compressed input and cannot substitute for a raw-frame
   deinterlacer. Preserve working Cedrus decoding and progressive playback.
5. Apply the qualified kernel/config/DTB combination to OpenWrt **6**, LibreELEC
   and Anotter. Compare module and effective DTB contents in SD-only, combined
   SD/eMMC payload and update files. Verify settings preservation during the
   SD-to-eMMC migration and update. Do not declare all images qualified from
   one LibreELEC boot or one Anotter compile.

## GPU upstream comparison and live result

The checked `h616-integration-v1` history for
`drivers/pmdomain/sunxi/sun50i-h6-prcm-ppu.c` contains the generic driver
[ca677196a91f6869169ef31252c00ceec6ac0754](https://github.com/jernejsk/linux-1/commit/ca677196a91f6869169ef31252c00ceec6ac0754),
authored by Andre Przywara. No additional T95H ordering fix was found in that
path/history. This is a scoped finding, not a claim about every upstream branch.
T95H uses a separate EL3-validated ANA provider; replacing it with the generic
register-writing driver is not part of this experiment.

`tools/experimental/gpu-start/start-hardware-ready` is the exact tested
LibreELEC 7.2.3 candidate. It holds the GPU before regulator registration can
trigger deferred probing, checks regulator voltages, registers and verifies
the ANA provider, then probes Panfrost. It verifies the render node belongs to
the expected GPU and keeps runtime PM on. It never unloads a live GPU and does
not change RAM clocks, voltage targets or thermal policy. Missing prerequisites
fail the hardware service rather than entering a restart loop.

Two eMMC warm boots passed:

| Boot ID | Panfrost ready | Early probe timeout |
|---|---|---|
| 4664f5fc-e6b7-4d3c-aa1c-1dea6362ed1b | approximately 15.8 s | absent |
| 569b7d81-ffad-456d-9c98-a9d90a4cd361 | approximately 16.0 s | absent |

Kodi, cpufreq and hardware service active; no failed units. Kodi reports
Mali-G31/Panfrost, OpenGL ES 3.1, Mesa 25.1.9. CPU passive limits restored to
70/75 °C after the test. Local full journals are under
`build/libreelec-flash-35196967768/live-audit/ready-gpu-boot{1,2}.txt`.

The single-boot wrapper restores the known-good 30/45-second startup override
on disk **before** executing the candidate. The checked-in wrapper additionally
uses atomic rename. The live system's next boot remains on that fallback;
the experimental 16-second path is not yet a persistent release change.
Cold power-on, SD boot and prolonged rendering remain to be qualified.

For Anotter and OpenWrt 6, port the ordering contract, not the LibreELEC paths
or fixed kernel guard. OpenWrt's WLAN worker also registers power resources:
place the hold before that registration and preserve networking independence.
After qualification, generate the same startup policy for SD, eMMC and updates.
