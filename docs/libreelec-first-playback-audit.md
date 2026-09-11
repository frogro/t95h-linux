# LibreELEC first playback audit — 2026-09-12

Live SD kernel: `7.2.3-t95h-libreelec`. Kodi uses Mali-G31/Panfrost.
The test film is H.264 Main Level 3.1, 1280x720 at 25 fps, with AAC-LC stereo.
Only metadata and selected file ranges were retrieved; no full source/copy integrity proof exists. The original file was not found at its previous development-disk path.

Kodi attempted the stateful V4L2 mem2mem H.264 decoder and failed to open it. The installed `libavcodec.so.60.3.100` contains `--disable-v4l2-request --disable-libudev` in its build configuration. The LibreELEC FFmpeg recipe enables the Request API for Allwinner but excluded our custom T95H project. The local adapter now includes T95H in that gate and in the matching deinterlace patch selection. Executing the upstream recipe before/after confirms T95H changes to `--enable-v4l2-request --enable-libudev`, while Allwinner, Rockchip and Generic retain their previous behavior.

The failed playback also produced invalid-packet errors; the missing Request API alone does not establish their cause. Kodi was stopped and restarted without rebooting the box, and Panfrost rendering returned. No successful hardware playback is claimed. Rebuild FFmpeg and affected dependents, repack SYSTEM, and validate on hardware before promoting.

Runtime WLAN regulatory fix: expose existing regulatory.db and regulatory.db.p7s from `/usr/lib/kernel-overlays/base/lib/firmware` in `/run/kernel-overlays/firmware`, then `iw reg reload` and `iw reg set DE`. Verified `country DE: DFS-ETSI`. This is volatile. Iwd crypto requirements remain unresolved in the installed kernel.
