# XR819 source preparation

Sources verified against the T95H 7.2.3 consolidated source-lock.json, then
0001-xradio-fix-32bit-read-lengths.patch and
0002-xradio-fix-vif-publication.patch applied with zero fuzz.

This package targets OpenWrt's mac80211 backports headers, not the raw 6.12
mac80211 headers. Compilation and hardware validation remain outstanding.
Firmware and the board's SDIO power/clock/regulator integration must be added
before enabling the package in the device profile. This source import alone
is not a working WLAN implementation.

OpenWrt mac80211 6.18.26 archive was checked against its package SHA256.
Its config/set_rts_threshold callbacks include radio_idx even on Linux 6.12.
The four corresponding declaration/definition guards therefore use an explicit
XRADIO_MAC80211_HAS_RADIO_IDX package flag; core kernel timer version checks
remain unchanged. This still requires a complete package compile.
source-sha256.json records the imported source before these API adaptations.
