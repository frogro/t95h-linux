#!/bin/sh
# One-time, exact-version bridge for an existing kernel6 sysupgrade handler.
set -eu
[ "$(id -u)" = 0 ]
[ "$(cat /tmp/sysinfo/board_name)" = t95h,h616-tvbox ]
case "$(uname -r)" in 6.*) ;; *) echo 'Only native OpenWrt kernel6 is supported.' >&2; exit 1;; esac
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
new=$base/platform-dual-update.sh
expected=@PLATFORM_SHA256@
[ "$(sha256sum "$new" | cut -d ' ' -f1)" = "$expected" ]
current=$(sha256sum /lib/upgrade/platform.sh | cut -d ' ' -f1)
case "$current" in
 "$expected") echo 'Upgrade handler is already current.'; exit 0;;
 ea1d688d9d0e8e44e058f9451e834deca04d724727f37ce5c499116d2c9bb65d) ;;
 *) echo 'Unknown installed upgrade handler; no change.' >&2; exit 1;;
esac
sh -n "$new"
[ "${1:---check}" = --apply ] || { echo 'PASS: known old handler; rerun with --apply to enable the corrected images.'; exit 0; }
backup=/root/t95h-platform-before-pmic305.sh
[ ! -e "$backup" ] || [ "$(sha256sum "$backup" | cut -d ' ' -f1)" = "$current" ]
[ -e "$backup" ] || cp -p /lib/upgrade/platform.sh "$backup"
cp "$new" /lib/upgrade/platform.sh.new
chmod 755 /lib/upgrade/platform.sh.new
[ "$(sha256sum /lib/upgrade/platform.sh.new | cut -d ' ' -f1)" = "$expected" ]
mv /lib/upgrade/platform.sh.new /lib/upgrade/platform.sh
sync
echo 'Upgrade handler updated. No firmware written; now use the matching SD/eMMC sysupgrade image with settings retained.'
