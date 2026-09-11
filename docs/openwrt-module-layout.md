# OpenWrt module layout correction

On 2026-09-11 the eMMC base-A-B image contained 34 normal kernel modules,
33 below kernel/ or updates/. OpenWrt kmodloader failed to resolve those by
name; direct insmod worked. The package now flattens all normal modules into
/lib/modules/<release>/ before depmod and metadata generation, in every
profile. Payload hashes are preserved, normalized-name collisions rejected,
modules.order rewritten and generated dependency paths checked. The private
ANA provider stays outside this directory for guarded late loading. Builtin
kernel drivers and the LibreELEC module layout are unchanged.

A temporary flat lookup directory on the running box allowed unmodified
kmodloader/modprobe to load all seven modular USB endpoint drivers and their
dependencies: mt76x0u, mt76x2u, mt7921u, rtw88_8821cu, r8152, r8153_ecm,
uvcvideo. Exit status was zero throughout. MT7612U and RTL8821CU also scanned
both bands successfully. Other devices were not attached, so loader success
is not a modem, Ethernet, video capture or throughput hardware validation.

Builtin USB drivers registered on the box include cdc_acm, cdc_ether,
cdc_mbim, cdc_ncm, cdc_wdm, option, qmi_wwan, rndis_host, asix,
ax88179_178a, snd-usb-audio, usbhid and usb-storage. They do not need modprobe.
Only configured drivers are covered; this is not support for every USB device
on the market. Video capture coverage here is UVC, not every proprietary
analog grabber chipset.

The flat package is shared by install images and sysupgrade artifacts.
No persistent live module files were relocated during the diagnostic test.
