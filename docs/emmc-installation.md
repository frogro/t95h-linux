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
The locked experimental eMMC SPL is included in eMMC payload generation.
The ordinary SD boot prefix is not replaced by it. Provenance is recorded in
boards/t95h/boot/emmc/lock.json; source-complete reproduction remains pending.

A separate SD SPL adaptation of the same reset/FIFO sequence was prepared.
The user observed boot on the second attempt; waiting time on the first attempt
was uncertain. This does not prove improved SD reliability. Existing SD load
retry behavior in the release is separate from this new experiment.

## Agreed installation SD layout and local command

Each profile is intended to offer a normal SD image and a second installation-SD
image with an additional partition containing the matching eMMC payload and its
verification manifest. Installation runs locally from the SD rootfs, with HDMI
console and USB keyboard; neither SSH nor an Internet connection is required.
The command is `t95h-install-emmc`, included only in the installation SD.

Before any target write, display:

> ACHTUNG: Das vorhandene Betriebssystem auf der eMMC und alle dort gespeicherten
> Daten werden gelöscht und durch OpenWrt ersetzt.

Require the exact interactive confirmation `EMMC LOESCHEN`; all other input
cancels. Booting the card must never trigger an unattended erase. Verify board,
SD root, target CID/size, unmounted target partitions and the full payload first.
An SD that chainloads eMMC root is not a suitable installation environment.

Preserve current SD OpenWrt root password, SSH configuration, host keys and
administrator authorized keys, network/AP configuration and LuCI access settings.
Do not regenerate an existing SSH identity during migration. This state is copied
locally and never uploaded to release assets. Do not migrate Android settings.
Storage-specific mount/UUID/boot configuration must instead be adapted for eMMC.
Validate restored access settings before reporting installation success. A DHCP
address is not guaranteed to stay identical. Subsequent SD and eMMC sysupgrade
packages must have separate media checks; SD packages must be rejected on eMMC.

## Current release boundary

The new build pipeline emits a normal SD image, a compressed three-partition
installation SD, and separate SD/eMMC sysupgrade packages from one kernel/rootfs
build. Both upgrade copy/validation paths are tested using regular files.
The installation worker has configuration-preservation and preflight tests;
a full hardware installation and eMMC sysupgrade test are still required.

The installer supports eMMC user-area boot selection; an unexpected hardware
boot-partition selection is rejected before writing. It clears remaining user
area and boot0/boot1, but does not claim erasure of RPMB or hidden flash storage.
After failed/interrupted installation, remain on SD and inspect the failure;
do not assume that eMMC is bootable. No automated reboot is performed.
Filesystem journaling and early fsck remain deferred.
