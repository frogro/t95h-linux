# eMMC status and installer design

## Observed hardware status

Direct eMMC cold boot without SD has been observed more than once on the test
T95H. Kernel logs show eMMC discovery near 2.3 seconds and root mounting near
3.1 seconds. These logs do not measure the preceding ROM/SPL/U-Boot time.
Boot reliability is not established. A later black-screen/network outage had
no captured crash cause; GPU startup is not a proven explanation.

The successful experimental combination uses:

- An eMMC-capable SPL based on reconstructed U-Boot 2024.04 sources.
- Reset/FIFO backport of upstream U-Boot commit
  [3e78f8f407a0](https://github.com/u-boot/u-boot/commit/3e78f8f407a0a0e7b50aa7eaa6f2f579f35e9837),
  authored by Jernej Skrabec and adjusted by Andre Przywara.
- Conservative SPL eMMC 25 MHz / 4-bit legacy settings.
- Existing BL31 and U-Boot executable with a control DT selecting eMMC and
  limiting its access to 25 MHz without high-speed/DDR capabilities.
- An eMMC-enabled Linux DT and identifiers distinct from the SD image.

Only the experimental SPL executable contains the reset/FIFO backport;
the existing U-Boot executable was not rebuilt with it. The complete source
lineage and reproducible bootloader build are still work in progress.
The binary experiment remains local and is not promoted into the SD release.

A separate SD SPL adaptation of the same reset/FIFO sequence was prepared.
The user observed boot on the second attempt; waiting time on the first attempt
was uncertain. This does not prove improved SD reliability. Existing SD load
retry behavior in the release is separate from this new experiment.

## One ThinkPad installer, no third partition

Use an SD with FAT boot and ext4 root. Its rootfs can hold the installation worker;
an additional installation partition is unnecessary. It must boot its own SD
rootfs, not chainload the eMMC rootfs that the installer would overwrite.

The intended user flow is to choose eMMC in the ThinkPad installer, boot the SD,
then enter the device address and root password. No manual SSH session is needed:
the installer creates the connection. Before writing it must verify board identity,
SD root, exact target CID/size, absence of mounted target partitions and the
complete storage-specific payload. Erasure of Android requires an explicit choice.

After verified transfer a detached on-device worker performs the write. The
ThinkPad reconnects to inspect the same operation receipt; it must not restart a
write merely because the connection dropped. Preserve selected access settings
and generate unique device keys. Boot-code handling and partition identities must
be explicit for eMMC. A SD sysupgrade package must be rejected on eMMC.

## Current release boundary

`installer.sh` currently starts SD builds and downloads verified release pairs.
`emmc-check` is read-only and requires a running SD-root system. The generic eMMC
installation worker, release-integrated eMMC image, and eMMC-specific sysupgrade
remain pending. No automatic flashing or destructive eMMC option is exposed by
the download installer yet. Filesystem journaling and early fsck are deferred.
