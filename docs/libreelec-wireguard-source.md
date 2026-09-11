# WireGuard source archive verification (2026-09-11)

LibreELEC 12.2.1 expects wireguard-tools 1.0.20250521 archive SHA256
6afe492647c3b0b2f68ab6df524e9e4290d03c34c3027e069e5bbc486949960e.
The current upstream cgit v-prefixed snapshot instead returns
e1b54c682c9734e81f8bd030eb00f2b33d3f09dfbd8397766d266c299c37e3fb.
The LibreELEC mirror returns 404.

The OpenWrt, Buildroot and MacPorts source mirrors independently supplied
archive SHA256 b6f2628b85b1b23cc06517ec9c74f82d52c4cdbd020f3dd2f00c972a1782950e.
All 123 non-directory entries (paths, modes, link targets and complete file
contents) matched both the current upstream snapshot and git archive of
upstream tag v1.0.20250521, commit e2ecaaa739144997ccff89d6ad6ec81698ea6ced.
The unavailable original LibreELEC archive was not compared. This establishes
source-tree equivalence to the tag, not equality of compressed archives.

The adapter uses https://sources.openwrt.org/wireguard-tools-1.0.20250521.tar.xz
with the verified mirror hash, only for the exact affected version and old
checksum. New upstream versions remain untouched. Hash verification remains
mandatory. Kernel and hardware patches are unchanged.
