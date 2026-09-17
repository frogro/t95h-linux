# PMIC-corrected boot firmware

Applies to native OpenWrt kernel 6, LibreELEC and AnotterKiosk. Historical
OpenWrt kernel 7 builders and their locked inputs remain unchanged.

The populated PMIC identifies as 0x60 (AXP305/806 family), not AXP313. The
reconstructed SPL now selects the AXP305 driver and its register encoding.
DRAM stays at 600 MHz, CPU SPL clock at 408 MHz. DCDCD is initialized to
1500 mV by this driver; this is an early SPL setting, not a claim that Linux
retains that voltage. The later inherited runtime DRAM voltage was 1360 mV.

DCDCC (GPU) uses the 600 mV + selector*10 mV encoding. An enabled 900 mV
initial state is stepped to 960 mV with readback. Existing 960/1100 mV is
retained. Unknown voltages, failed PMIC identification and failed writes still
abort: those are hardware protection checks, not disposable boot markers.

`sd.toc0` is the exact locally booted and stress-tested candidate
391e7661…; eMMC is derived from the same source with MMC slot 2 enabled,
25 MHz/4-bit early eMMC limits, GPU gate and MMC FIFO/reset fixes retained.
The new eMMC binary is built and signature-verified, **not hardware-tested**.
No private signing key is included. Configs use a normal distro boot command;
the historical marker-writing U-Boot command was not present in the SPL.
Only the 40 KiB SPL changes. FIT, BL31, U-Boot proper and partition tables stay.

Source recipe: reconstructed U-Boot 2024.04 baseline, the existing
`../emmc/reset-fifo-backport.patch` and `early-gpu-gate.patch`, plus
`pmic-source.patch`, with sd.config/emmc.config. The private legacy downstream
firmware is still not source-completely reproduced. This correction does not
change that limitation. `gpu-supply.patch` is an explanatory subset of
pmic-source.patch; do not apply it twice.

`lock.json` binds old/new prefixes, SPL and firmware-region hashes. Anotter and
LibreELEC change only MBR identifiers/layout after this validation. Their
combined SD/eMMC installers are assembled from these corrected component images.
