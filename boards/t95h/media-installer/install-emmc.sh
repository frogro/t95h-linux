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
mode=${1:-install}
case "$mode" in install) ;; --update) [ "$os" = anotter ] || fail 'Update-Modus nur für Anotter.';; *) fail 'Aufruf: install-emmc.sh [--update]';; esac
[ "$#" -le 1 ] || fail 'Zu viele Argumente.'
case "$os" in
 anotter) boot=/boot/firmware; root=/; confmax=94371840;;
 libreelec) boot=/flash; root=/storage; confmax=419430400;;
 openwrt6) boot=/; root=/; confmax=94371840; case "$(uname -r)" in 6.*) ;; *) fail 'OpenWrt Kernel 6 erforderlich.';; esac;;
 *) fail 'Unbekanntes System.';;
esac
# OpenWrt compares its archive; other OSes use the bundled tree comparator.
if [ "$os" != openwrt6 ]; then
 command -v python3 >/dev/null || fail 'Python für Konfigurationsvergleich fehlt.'
 python3 "$base/compare-config.py" --check || fail 'Konfigurationsvergleich nicht ausführbar.'
fi
# Resolve real mounted filesystems through major/minor, not /dev aliases.
mounted_device() {
 mm=$(awk -v p="$1" '$5==p {print $3;exit}' /proc/self/mountinfo)
 [ -n "$mm" ] && basename "$(readlink -f /sys/dev/block/$mm)"
}
bdev=$(mounted_device "$boot") || fail 'Bootmedium fehlt.'
if [ "$os" = openwrt6 ]; then
 case "$bdev" in mmcblk[0-9]p2) bdev=${bdev%p2}p1;; *) fail 'OpenWrt-Root nicht auf MMC-Partition 2.';; esac
fi
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
mkdir "$work/new" "$work/saved" "$work/old"
cleanup() {
 umount "$work/new" 2>/dev/null || :
 umount "$work/old" 2>/dev/null || :
 for n in 0 1; do echo 1 > /sys/class/block/${disk}boot$n/force_ro 2>/dev/null || :; done
}
trap cleanup EXIT
umask 077
printf 'ACHTUNG: Das vorhandene Betriebssystem und ALLE Daten auf der eMMC werden gelöscht.\n'
printf 'Ziel /dev/%s (%s MiB), neues System: %s.\n' "$disk" "$((sectors / 2048))" "$os"
if [ "$mode" = --update ]; then
 # Only read the existing target FAT; never use the rescue SD's defaults.
 [ "$(od -An -tx1 -j 440 -N 4 "/dev/$disk" | tr -d ' \n')" = 020095a0 ] || fail 'Kein T95H-Anotter-eMMC-Layout.'
 mount -t vfat -o ro,umask=0077 "/dev/${disk}p1" "$work/old"
 [ -f "$work/old/kioskbrowser.ini" ] && [ -f "$work/old/boot/boot.scm" ] || fail 'Kein vorhandenes Anotter-System auf eMMC.'
 boot=$work/old
 printf 'UPDATE: Einstellungen der vorhandenen eMMC werden übernommen. '
else
 printf 'Einstellungen dieser SD werden übernommen. '
fi
printf 'Zum Bestätigen EMMC LOESCHEN eingeben: '
IFS= read -r answer || fail 'Abgebrochen.'
[ "$answer" = 'EMMC LOESCHEN' ] || fail 'Abgebrochen; nichts geschrieben.'
# Snapshot settings before any target write. Do not copy boot files/fstab/UUIDs.
: > "$work/list"
if [ "$os" = openwrt6 ]; then
 sysupgrade -b "$work/sysupgrade.tgz" || fail 'Konfigurationssicherung fehlgeschlagen.'
 echo sysupgrade.tgz > "$work/list"
 source=$work
elif [ "$os" = anotter ]; then
 for f in kioskbrowser.ini wpa_supplicant.conf authorized_keys id_rsa id_ed25519 ssh_host_rsa_key ssh_host_rsa_key.pub ssh_host_ed25519_key ssh_host_ed25519_key.pub splash.png www-public; do
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
if [ "$mode" = --update ]; then
 umount "$work/old"
 # Keep only a configuration recovery copy on the installer SD, never a full image.
 recovery="$base/anotter-settings-$(date +%Y%m%d-%H%M%S)-$$.tar"
 (set -C; cat "$work/config.tar" > "$recovery") || fail 'Konfigurationssicherung auf Installer-SD fehlgeschlagen.'
 cmp "$work/config.tar" "$recovery" || fail 'Konfigurationssicherung unvollständig.'
 sync
 printf 'Einstellungen gesichert: %s\n' "$recovery"
fi
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
if [ "$os" = anotter ] || [ "$os" = openwrt6 ]; then
 mount -t vfat -o rw,umask=0077 "/dev/${disk}p1" "$work/new"
else
 mount -t ext4 -o rw,noatime "/dev/${disk}p2" "$work/new"
fi
tar -xf "$work/config.tar" -C "$work/new"
# Content check includes nested web/Kodi files and symlinks, not FAT Unix modes.
if [ "$os" = openwrt6 ]; then
 [ "$(sha256sum "$work/saved/sysupgrade.tgz" | cut -d ' ' -f1)" = "$(sha256sum "$work/new/sysupgrade.tgz" | cut -d ' ' -f1)" ] || fail 'Konfigurationsvergleich fehlgeschlagen.'
else
 while IFS= read -r f; do python3 "$base/compare-config.py" -r "$work/saved/$f" "$work/new/$f" || fail 'Konfigurationsvergleich fehlgeschlagen.'; done < "$work/list"
fi
sync
umount "$work/new"
printf 'PASS: eMMC installiert und Einstellungen übernommen.\nJetzt poweroff, Strom trennen, SD entfernen und wieder einschalten.\n'
