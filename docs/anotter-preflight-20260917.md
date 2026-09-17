# AnotterKiosk preflight, 2026-09-17

User confirms first successful display of the official KittenLabs welcome page.
Read-only SSH audit of t95h-kiosk.local (192.168.178.180), kernel
7.2.3-t95h-anotter-de33, Debian 13: no failed units; lightdm, nginx,
t95h-hardware and t95h-audio active. Panfrost bound, GPU runtime control on and
runtime status active; analog output switches on; snd_usb_audio registered.
Early DRM/Panfrost probe failures were followed by successful initialization.
No stress test, reboot or live configuration change was performed.

Two additional issues were found before dispatch:

- ntpsec-ntpdate's if-up hook and the upstream ntpdate service computed the same
  approximately 13523907-second offset concurrently and applied it twice. The
  journal records first April -> September 2026, then September -> February 2027.
  The service now uses the exact same /run/lock/ntpsec-ntpdate flock as the Debian
  hook. The lock encloses the query as well as the time adjustment. Existing
  upstream servers and network-wait behavior are retained.
- Debian's 90-alsa-restore.rules contained two alsa_restore_go labels and no
  alsa_restore_std label. The second label is corrected. An already-correct
  package is retained; unknown layouts abort preparation. udevadm verify passes
  against the patched rule extracted from the actual image.

Anotter now owns its hardware unit rather than copying LibreELEC's unit, which
recently gained a LibreELEC-only cpufreq.service start. CPU policy, GPU timings,
thermal limits, browser landing page and SSH provisioning remain unchanged.

108 repository tests and repository guards pass. These preparation changes feed
both SD/eMMC images and the combined installer. Internal WLAN remains disabled;
a complete settings-preserving image updater remains outstanding. Those are not
claimed implemented by this maintenance build. The rebuilt image still needs a
boot test confirming one correct time adjustment and no ALSA rule warnings.
