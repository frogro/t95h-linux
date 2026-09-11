# LibreELEC playback and WLAN test build — 12 September 2026

This build enables the V4L2 Request API in FFmpeg for the T95H project, matching
LibreELEC's Allwinner path. The first image had explicitly disabled this API:
Panfrost rendered Kodi, but Cedrus could not decode the test movie through Kodi.

It also builds in iwd's required crypto interfaces and algorithms. A startup
service exposes the existing signed regulatory database after firmware setup and
requests a reload without forcing a country. The same database reload was tested
live; the new kernel and hardware-decoding path still require hardware testing.

Bootloader, DTB, thermal limits and the 60/120-second hardware startup sequence
remain unchanged for a comparable test. The build produces SD, eMMC payload and
SD-with-eMMC-installer candidates. Automatic storage expansion is not part of
this change. Existing user settings, including disabled hardware decoding from
the software-playback test, may need adjustment when testing an upgraded system.

Validation before dispatch: 62 tests passed; the exact Linux 7.2.3 Kconfig
retained every requested iwd option after olddefconfig. The upstream FFmpeg recipe
was executed for T95H, Allwinner, Rockchip and Generic to verify the changed gate.

The old checkpoint cannot be treated as a packaging-only migration: kernel and
compiled multimedia inputs changed. This dispatch starts fresh and uses the
existing package-boundary checkpoints between phases. It creates test artifacts,
not a claim that hardware decoding, WLAN or eMMC installation has passed.

ARD/ZDF API failures and missing YouTube API configuration are separate add-on
issues and are not fixed by this build. IPTV Simple loaded both test channels.
