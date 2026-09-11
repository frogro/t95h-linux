# eMMC SPL GPU initialization correction

The T95H booted OpenWrt from eMMC but lost connectivity when standard Panfrost
was probed, including a manual probe after nine minutes. The same kernel,
Linux DTB, ANA provider and runtime script successfully initialized Panfrost
when booted from SD. Both boot prefixes were captured read-only.

The SD SPL retained an early write of zero to GPU gate register 0x07010254,
followed by DSB SY. This binary-only inherited operation was missing from the
reconstructed eMMC SPL source. U-Boot and BL31 payloads were byte-identical.
The source patch now restores the operation after ANA/calibration setup.
The existing eMMC 25 MHz/4-bit SPL settings and reset/FIFO fix are retained.

The previous signed SPL was reproduced byte-for-byte using the existing key
before signing the corrected build. The new signed payload was disassembled
to verify the effective register address, zero write and barrier. Repository
checks lock both patches and the signed SPL; a regression test checks the
actual signed firmware instruction sequence. Compiler/layout changes require
review and an updated instruction-level test, not removal of this check.

On the test box only the 40960-byte SPL at offset 8192 was replaced after a
verified boot-prefix backup. All 4 MiB were read back and matched the expected
prefix. Partitions, Linux kernel and OpenWrt were not replaced. The box rebooted
from eMMC; manual Panfrost startup passed at 120.26 s with renderD128 present,
432 MHz GPU and 200 MHz bus. SSH remained available with the same boot ID for
39 minutes at the last check. This was not a rendering stress test or a cold
power-cycle test. GPU autostart on the test eMMC remains disabled pending that
follow-up. Release runtime defaults remain unchanged.

New eMMC installation payloads contain the corrected SPL. Sysupgrade only
updates FAT/rootfs and cannot deliver a boot-prefix correction to existing
installations. Those require a separate guarded SPL repair or reinstallation.
The correction does not make bootloader source reproduction complete: the
existing proprietary/incompletely reproduced binary dependency limitations
remain recorded in the boot lock.

## Rendering follow-up, 2026-09-11

After a manual power cycle following sysupgrade, the eMMC system initialized
standard Panfrost successfully using the guarded late service. Mesa 25.2.4
reported Mali-G31 (Panfrost), OpenGL ES 3.1. An offscreen kmscube smoke test
completed, followed by `kmscube -D /dev/dri/renderD128 -O -v 1024x768 -g -c 30000`.
The latter reported 29999 frames in 109.06 seconds (275.07 fps), exit 0.
SSH and the boot ID remained unchanged; no new GPU faults appeared.
Existing WLAN missed interrupts and SDIO data errors remain a separate open
issue; this result does not establish long-term stability or HDMI scanout.

The test box GPU service was re-enabled for subsequent boots. Fresh base-B
and base-A-B profiles already enable this service; image assembly now rejects
a missing or incorrect S99t95h-gpu symlink. The existing 120-second minimum
and readiness checks remain unchanged. Autostart after another reboot has not
yet been tested in this follow-up. The earlier automatic sysupgrade reboot
failed to return and required the manual power cycle; that issue remains open.
