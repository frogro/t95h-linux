# T95H LibreELEC – SD and eMMC installation candidate

This package reuses the completed LibreELEC kernel and SYSTEM from the successful
source run identified in `repackage-source.json`. It does not rebuild Kodi or
change the kernel. The Anotter DE33 experiment is not included; this is the
baseline for the first Kodi hardware test.

Files:
- `…-sd.img.gz`: run from SD.
- `…-sd-emmc-installer.img.gz`: run from SD and explicitly install to eMMC.
- `…-emmc.img.gz`: internal payload/raw eMMC image, not a bootable installer SD.

Decompress before flashing. See the [installation guide](https://github.com/frogro/t95h-linux/blob/main/docs/media-emmc-installation.md).
The eMMC installer warns before deleting the existing OS and data and copies the
current SD's Kodi/network/SSH settings. Large media libraries are not migrated.

These images and the new installer are experimental and have not yet passed
T95H hardware installation tests. First test SD boot, HDMI, Kodi, Ethernet, input,
audio and video playback. Separate T95H OS-update support is not yet released.
Do not use an OpenWrt sysupgrade file. The eMMC capacity must fit the target image;
the installer validates the actual target rather than assuming a device number.
