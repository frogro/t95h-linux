# T95H AnotterKiosk – DE33 display candidate

Download the SD image, decompress `.img.gz`, and write the `.img` to the entire
SD card. Configure `kioskbrowser.ini` and `authorized_keys` on T95HKIOSK before
booting. See the [installation guide](https://github.com/frogro/t95h-linux#image-herunterladen-und-auf-sd-schreiben).

This build includes the DE33 display/scaler/RCQ changes tested with direct Cedrus
NV12 output on one T95H and the matching IOMMU binding. It also accepts already
initialized, verified Panfrost/provider bindings. The default Anotter webpage,
SSH key provisioning, network handling and original thermal limits are retained.

This is an experimental hardware candidate. Native video tests improved mouse
feedback but did not prove Chromium hardware video decoding or 60 unique frames
per second. Deskreen in Chromium remained slower than native output. Cold-boot
reliability, wider HDMI/audio compatibility and the new complete image still
need device testing. No OpenWrt or LibreELEC kernel promotion is implied.

The tested streaming recipe is separate from the default kiosk and has no
personal server address, USB binding or SSH keys preconfigured in the image.

The release also includes a normal SD image, a raw eMMC payload and a dedicated
SD with the offline eMMC installer. That installation path is new and requires
its own device test. It preserves the SD's kiosk/SSH boot configuration while
using the new eMMC boot identifiers. See the
[eMMC instructions](https://github.com/frogro/t95h-linux/blob/main/docs/media-emmc-installation.md).
The normal SD image does not contain the installer payload.

GStreamer tools/plugins and `t95h-desktop-view` are now included for optional
native display. The sending PC still needs its own capture, encoder and go2rtc.
VirtualHere is not bundled. The new packaged player needs a full-image test;
the live evidence concerns the matching pipeline, not automatic setup on every PC.

Internal XR819 WLAN is enabled in the device tree. Set [wifi] in kioskbrowser.ini
or supply wpa_supplicant.conf on FAT, as documented by AnotterKiosk. The connection
starts after hardware initialization; no configured SSID leaves Ethernet unchanged.
The eMMC installer preserves the separate WLAN configuration too. Known XR819
interrupt issues are not claimed fixed; this complete image needs WLAN testing.

UPDATE.md describes the image-flashing procedure with T95H settings retention.
The release's update-anotter-sd.py preserves supported FAT settings for either SD
variant; install-emmc.sh --update on the combined SD preserves the existing eMMC's
settings. Both retain a small private settings recovery copy, not a full old image.
These are T95H helpers, not an official upstream in-place updater. Rootfs edits and
extra packages are not preserved; offline hardware updates still need device tests.
The experimental unsafe upstream script is not included.
The prior NTP concurrency and ALSA rule fixes remain included.
