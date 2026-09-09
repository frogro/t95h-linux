#!/bin/sh
# Only software block protection; no mounts and no storage data writes.
failed=0
for d in /sys/class/block/mmcblk*; do
 [ -e "$d" ] || continue
 name=${d##*/}
 case "$name" in *rpmb*) continue;; esac
 base=${name%%boot*}; base=${base%%p*}
 [ "$(cat "/sys/class/block/$base/device/type" 2>/dev/null)" = MMC ] || continue
 /usr/sbin/t95h-emmc-block-readonly "/dev/$name" || failed=1
done
exit "$failed"
