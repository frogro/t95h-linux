# Boot consoles

Image builds must apply tools/configure-boot-console.py to boot.scm before FAT assembly.
Default dual mode retains UART kernel output and adds HDMI kernel output once the
framebuffer console registers. HDMI is last, so /dev/console userspace output goes
there. This does not duplicate every OpenWrt service log to both outputs; logd
messages remain accessible via logread. Keep ttyS0 and tty1 login entries.
UART-only and HDMI-only are selectable build options. Early UART output remains
independent of framebuffer initialization. No persistent boot-marker recording is added.

SD test: scripts/test-dual-console-sd.py in the enclosing project. It saves the
FAT partition and boot prefix, updates only boot.scm through a FAT mount, then
remounts read-only to verify. Restoring the saved boot.scm on the FAT boot partition
reverts the console change. Hardware validation is pending.

## Tested binary lineage

`tested-prefix-lock.json` records the exact 4 MiB prefix of the tested Cedrus
image and its partition table. Bytes after the first 512-byte sector match the
historical `ana-smc-compare/A/boot-prefix.bin` exactly; the FAT/rootfs layout only
changed the MBR. This is verified local binary provenance, not yet a standalone
source recipe or a downloadable Actions input. Never replace it with a different
SPL/BL31 experiment simply because that experiment was created later.

## Experimental SD initialization retry

All profiles use the same `scripts/boot.scm`, with the selected console mode
applied at assembly. `boot.scm.txt` is the readable source of that legacy U-Boot
script. After the outer boot.scr has loaded it, it waits one second and makes
at most three attempts: select MMC 0, rescan, load Image and DTB, and boot.
A failed attempt is followed by a one-second delay. After three failures the
script stops in the existing sleep loop. No SD power rail, SPL, BL31, raw boot
prefix, persistent marker or Linux driver is changed.

On 2026-09-09 the identical dual-console payload installed live was followed by
two user-reported cold starts succeeding on their first power-on. This is an
experimental improvement, not proof of a fixed coldboot problem. Neither the
successful internal attempt number nor whether the delay or rescan helped was
captured. Failures before this script is loaded cannot be recovered here.
Both newly assembled install images and their derived sysupgrade packages carry
this script; previously produced artifacts must be repackaged to include it.
