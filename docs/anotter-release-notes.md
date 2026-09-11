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
