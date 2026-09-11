#!/bin/sh
# Run explicitly from the dedicated SD payload partition. Never at boot.
if ! (set -o pipefail) 2>/dev/null; then exec bash "$0" "$@"; fi
set -eu
set -o pipefail
fail() { echo "STOP: $*" >&2; exit 1; }
[ "$(id -u)" = 0 ] || fail 'Als root starten.'
[ -t 0 ] || fail 'Interaktive Bestätigung erforderlich.'
[ "$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)" = t95h,h616-tvbox ] || fail 'Falsches Board.'
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
(cd "$base" && sha256sum -c SHA256SUMS) || fail 'Installationspaket beschädigt.'
os=$(cat "$base/os")
case "$os" in
 anotter) boot=/boot/firmware; root=/; confmax=94371840;;
 libreelec) boot=/flash; root=/storage; confmax=419430400;;
 *) fail 'Unbekanntes System.';;
esac
# Resolve real mounted filesystems through major/minor, not /dev aliases.
mounted_device() {
 mm=$(awk -v p="$1" '$5==p {print $3;exit}' /proc/self/mountinfo)
 [ -n "$mm" ] && basename "$(readlink -f /sys/dev/block/$mm)"
}
bdev=$(mounted_device "$boot") || fail 'Bootmedium fehlt.'
case "$bdev" in mmcblk[0-9]p1) sd=${bdev%p1};; *) fail 'Boot muss auf SD-Partition 1 liegen.';; esac
[ "$(cat /sys/class/block/$sd/device/type)" = SD ] || fail 'Nur von SD installieren.'
[ "$(mounted_device "$root")" = "${sd}p2" ] || fail 'Root/Storage liegt nicht auf derselben SD.'
[ "$(mounted_device "$base")" = "${sd}p3" ] || fail 'Skript direkt aus der dritten SD-Partition starten.'
size=$(cat "$base/raw-bytes")
case "$size" in ''|*[!0-9]*) fail 'Ungültige Imagegröße.';; esac
[ "$size" -gt 4194304 ] && [ $((size % 1048576)) = 0 ] || fail 'Imagegröße nicht ausgerichtet.'
# Check the complete decompressed stream before touching the target.
[ "$(gzip -dc "$base/emmc.img.gz" | sha256sum | cut -d ' ' -f1)" = "$(cat "$base/raw-sha256")" ] || fail 'Imageprüfung fehlgeschlagen.'
disk=
for d in /sys/class/block/mmcblk[0-9]; do
 [ -r "$d/device/type" ] || continue
 [ "$(cat "$d/device/type")" = MMC ] || continue
 [ -z "$disk" ] || fail 'Mehrere eMMC-Geräte.'
 disk=${d##*/}
done
[ -n "$disk" ] && [ "$disk" != "$sd" ] || fail 'Kein eindeutiges eMMC-Ziel.'
cid=$(cat /sys/class/block/$disk/device/cid)
sectors=$(cat /sys/class/block/$disk/size)
[ "$sectors" -ge $((size / 512)) ] && [ $((sectors % 2048)) = 0 ] || fail 'eMMC zu klein oder nicht unterstützt.'
check_target() {
 [ "$(cat /sys/class/block/$disk/device/cid)" = "$cid" ] &&
 [ "$(cat /sys/class/block/$disk/size)" = "$sectors" ] &&
 [ "$(cat /sys/class/block/$disk/device/type)" = MMC ] &&
 [ "$(cat /sys/class/block/$disk/ro)" = 0 ] || fail 'Ziel geändert oder schreibgeschützt.'
 for d in /sys/class/block/$disk /sys/class/block/${disk}p* /sys/class/block/${disk}boot*; do
  [ -r "$d/dev" ] || continue
  mm=$(cat "$d/dev")
  if awk -v mm="$mm" '$3==mm {found=1} END {exit !found}' /proc/self/mountinfo; then fail 'eMMC ist eingehängt.'; fi
  [ -z "$(ls -A "$d/holders")" ] || fail 'eMMC wird verwendet.'
 done
 if grep -q "/dev/$disk" /proc/swaps; then fail 'eMMC-Swap ist aktiv.'; fi
}
check_target
"$base/check-boot-selection" "/dev/$disk" || fail 'Bootauswahl nicht unterstützt.'
for n in 0 1; do
 b=${disk}boot$n
 [ -b "/dev/$b" ] && [ -w /sys/class/block/$b/force_ro ] || fail 'Bootbereich fehlt.'
 s=$(cat /sys/class/block/$b/size)
 [ "$s" -gt 0 ] && [ $((s % 2048)) = 0 ] || fail 'Bootbereichgröße ungültig.'
done
work=/tmp/t95h-emmc-install.lock
mkdir "$work" 2>/dev/null || fail 'Installationsauftrag vorhanden; vor erneutem Versuch Zustand prüfen.'
mkdir "$work/new" "$work/saved"
cleanup() {
 umount "$work/new" 2>/dev/null || :
 for n in 0 1; do echo 1 > /sys/class/block/${disk}boot$n/force_ro 2>/dev/null || :; done
}
trap cleanup EXIT
umask 077
printf 'ACHTUNG: Das vorhandene Betriebssystem und ALLE Daten auf der eMMC werden gelöscht.\n'
printf 'Ziel /dev/%s (%s MiB), neues System: %s.\n' "$disk" "$((sectors / 2048))" "$os"
printf 'Einstellungen dieser SD werden übernommen. Zum Bestätigen EMMC LOESCHEN eingeben: '
IFS= read -r answer || fail 'Abgebrochen.'
[ "$answer" = 'EMMC LOESCHEN' ] || fail 'Abgebrochen; nichts geschrieben.'
# Snapshot settings before any target write. Do not copy boot files/fstab/UUIDs.
: > "$work/list"
if [ "$os" = anotter ]; then
 for f in kioskbrowser.ini authorized_keys id_rsa id_ed25519 ssh_host_rsa_key ssh_host_rsa_key.pub ssh_host_ed25519_key ssh_host_ed25519_key.pub splash.png www-public; do
  [ ! -e "$boot/$f" ] || echo "$f" >> "$work/list"
 done
 source=$boot
else
 systemctl stop kodi
 for f in .config .cache .kodi; do [ ! -e "$root/$f" ] || echo "$f" >> "$work/list"; done
 source=$root
fi
# Reject oversized settings while the original target is still intact.
bytes=$(while IFS= read -r f; do du -sk "$source/$f"; done < "$work/list" | awk '{n+=$1} END {printf "%.0f",n*1024}')
[ "$bytes" -le "$confmax" ] || fail 'Einstellungen zu groß für das Ziel; separat sichern.'
avail=$(df -Pk "$work" | awk 'NR==2 {print $4}')
[ "$avail" -gt $((bytes / 512 + 16384)) ] || fail 'Zu wenig RAM für Konfigurationssicherung.'
tar -cf "$work/config.tar" -C "$source" -T "$work/list"
tar -xf "$work/config.tar" -C "$work/saved"
check_target
# Full image write. pipefail prevents a truncated gzip stream reporting success.
gzip -dc "$base/emmc.img.gz" | dd of="/dev/$disk" bs=1048576 conv=fsync
[ "$(dd if="/dev/$disk" bs=1048576 count="$((size / 1048576))" | sha256sum | cut -d ' ' -f1)" = "$(cat "$base/raw-sha256")" ] || fail 'Image-Rückprüfung fehlgeschlagen.'
tail=$((sectors / 2048 - size / 1048576))
if [ "$tail" -gt 0 ]; then dd if=/dev/zero of="/dev/$disk" bs=1048576 seek="$((size / 1048576))" count="$tail" conv=fsync,notrunc; fi
for n in 0 1; do
 b=${disk}boot$n
 echo 0 > /sys/class/block/$b/force_ro
 dd if=/dev/zero of="/dev/$b" bs=1048576 count="$(( $(cat /sys/class/block/$b/size) / 2048 ))" conv=fsync
 echo 1 > /sys/class/block/$b/force_ro
done
"$base/reread-partitions" "/dev/$disk"
if [ "$os" = anotter ]; then
 mount -t vfat -o rw,umask=0077 "/dev/${disk}p1" "$work/new"
else
 mount -t ext4 -o rw,noatime "/dev/${disk}p2" "$work/new"
fi
tar -xf "$work/config.tar" -C "$work/new"
# Content check includes nested web/Kodi files and symlinks, not FAT Unix modes.
while IFS= read -r f; do diff -r "$work/saved/$f" "$work/new/$f" || fail 'Konfigurationsvergleich fehlgeschlagen.'; done < "$work/list"
sync
umount "$work/new"
printf 'PASS: eMMC installiert und Einstellungen übernommen.\nJetzt poweroff, Strom trennen, SD entfernen und wieder einschalten.\n'
