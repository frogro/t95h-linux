# T95H FAT64/ext4 SD sysupgrade v1. No bootloader or partition-table writes.
REQUIRE_IMAGE_METADATA=1
RAMFS_COPY_BIN="${RAMFS_COPY_BIN} sha256sum readlink dirname wc tr cmp head tee mkfifo mktemp"


# Test-only progress: RAM file plus best-effort UDP to the paired ThinkPad.
RAMFS_COPY_BIN="$RAMFS_COPY_BIN /usr/libexec/t95h-upgrade-report"
if [ -f /tmp/t95h-upgrade-progress.env ]; then
 . /tmp/t95h-upgrade-progress.env
 export T95H_REPORT_IP T95H_REPORT_PORT T95H_REPORT_TOKEN
fi
t95h_progress() {
 local msg="$*"
 printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$msg" >> /tmp/t95h-upgrade-progress.log
 printf 'T95H: %s\n' "$msg" >&2
 if [ -x /usr/libexec/t95h-upgrade-report ]; then /usr/libexec/t95h-upgrade-report event "$msg" || :; fi
}
t95h_meter() {
 if [ -x /usr/libexec/t95h-upgrade-report ]; then /usr/libexec/t95h-upgrade-report stream "$1"; else cat; fi
}
t95h_backup_check() (
 set -o pipefail
 [ -n "$UPGRADE_BACKUP" ] || { t95h_progress 'CONFIG: no retention requested'; exit 0; }
 [ -r "$UPGRADE_BACKUP" ] || { t95h_error 'CONFIG backup missing'; exit 1; }
 local names path tmp
 tmp="$(mktemp -d /tmp/t95h-config-check.XXXXXX)" || exit 1
 trap 'rm -rf "$tmp"' EXIT
 names="$(tar -tzf "$UPGRADE_BACKUP" 2> "$tmp/tar-errors")" || { t95h_error 'CONFIG invalid archive'; exit 1; }
 [ ! -s "$tmp/tar-errors" ] || { t95h_error 'CONFIG archive listing warnings'; exit 1; }
 [ -n "$names" ] || { t95h_error 'CONFIG empty archive'; exit 1; }
 while IFS= read -r path; do
 case "$path" in /*|..|../*|*/../*|*/..) t95h_error 'CONFIG unsafe archive path'; exit 1;; esac
 done <<EOL
$names
EOL
 # Validate extraction in tmpfs before touching partitions. No secret contents logged.
 tar -xzf "$UPGRADE_BACKUP" -C "$tmp" || { t95h_error 'CONFIG extraction test failed'; exit 1; }
 sha256sum "$UPGRADE_BACKUP" | cut -d ' ' -f 1 > /tmp/t95h-config-sha256 || exit 1
 t95h_progress 'CONFIG archive and extraction verified'
)

t95h_error() { t95h_progress "ERROR: $*"; return 1; }
t95h_stream() { tar -xOf "$1" "$2"; }
t95h_hash() { sha256sum | cut -d ' ' -f 1; }
t95h_manifest() {
 local magic extra
 local meta="$(t95h_stream "$1" manifest)" || return 1
 [ "$(printf '%s\n' "$meta" | wc -l)" = 7 ] || return 1
 {
 read -r magic
 read -r T95H_PREFIX
 read -r T95H_BOOT_GZ
 read -r T95H_ROOT_GZ
 read -r T95H_BOOT_RAW
 read -r T95H_ROOT_RAW
 read -r extra
 } <<EOM
$meta
EOM
 [ "$magic" = T95H-SD-UPGRADE-1 ] && [ "$extra" = '67108864 2025848832' ] || return 1
 for extra in "$T95H_PREFIX" "$T95H_BOOT_GZ" "$T95H_ROOT_GZ" "$T95H_BOOT_RAW" "$T95H_ROOT_RAW"; do
 [ "${#extra}" = 64 ] || return 1
 case "$extra" in *[!0-9a-f]*) return 1;; esac
 done
}
t95h_validate_archive() (
 set -o pipefail
 local image="$1" member expected
 [ -f "$image" ] || exit 1
 [ "$(tar -tf "$image")" = "manifest
boot.gz
root.gz" ] || exit 1
 t95h_manifest "$image" || exit 1
 for member in boot root; do
 if [ "$member" = boot ]; then expected="$T95H_BOOT_GZ"; else expected="$T95H_ROOT_GZ"; fi
 [ "$(t95h_stream "$image" "$member.gz" | t95h_hash)" = "$expected" ] || exit 1
 done
)
# Count and hash the same decompressed stream. Both checks remain mandatory.
t95h_check_raw() (
 set -o pipefail
 local image="$1" member="$2" expected="$3" size="$4" tmp raw counter
 tmp="$(mktemp -d /tmp/t95h-upgrade-check.XXXXXX)" || exit 1
 trap 'rm -rf "$tmp"' EXIT
 mkfifo "$tmp/count-pipe" || exit 1
 wc -c < "$tmp/count-pipe" > "$tmp/size" &
 counter=$!
 raw="$(t95h_stream "$image" "$member.gz" | gzip -dc | tee "$tmp/count-pipe" | t95h_meter "$member-validate" | t95h_hash)"
 local result=$?
 t95h_progress "$member validation pipeline rc=$result"
 wait "$counter" || exit 1
 [ "$result" = 0 ] && [ "$(cat "$tmp/size")" = "$size" ] && [ "$raw" = "$expected" ]
)
t95h_validate_payload() (
 t95h_validate_archive "$1" || exit 1
 t95h_manifest "$1" || exit 1
 echo 'T95H: prüfe FAT (Größe und SHA256 in einem Durchlauf).' >&2
 t95h_check_raw "$1" boot "$T95H_BOOT_RAW" 67108864 || exit 1
 echo 'T95H: prüfe Rootfs (Größe und SHA256 in einem Durchlauf); dies kann mehrere Minuten dauern.' >&2
 t95h_check_raw "$1" root "$T95H_ROOT_RAW" 2025848832 || exit 1
 echo 'T95H: vollständige Paketprüfung bestanden.' >&2
)

t95h_target() {
 local node rootdev bootdev rootmm
 [ "$(tr '\000' '\n' < /proc/device-tree/compatible | head -n 1)" = 't95h,h616-tvbox' ] || return 1
 rootmm="$(awk '$5=="/" && $0 ~ / - ext4 / { print $3; exit }' /proc/self/mountinfo)"
 [ -n "$rootmm" ] || return 1
 node="$(readlink -f "/sys/dev/block/$rootmm")"
 rootdev="${node##*/}"
 case "$rootdev" in mmcblk[0-9]p2) ;; *) return 1;; esac
 T95H_DISK="${rootdev%p2}"
 t95h_target_check "$T95H_DISK"
}
t95h_target_check() {
 local d="$1"
 case "$d" in mmcblk[0-9]) ;; *) return 1;; esac
 [ "$(cat /sys/class/block/$d/device/type)" = SD ] || return 1
 [ "$(cat /sys/class/block/${d}p1/start)" = 8192 ] &&
 [ "$(cat /sys/class/block/${d}p1/size)" = 131072 ] &&
 [ "$(cat /sys/class/block/${d}p2/start)" = 139264 ] &&
 [ "$(cat /sys/class/block/${d}p2/size)" = 3956736 ] || return 1
 [ -b "/dev/${d}p1" ] && [ -b "/dev/${d}p2" ] || return 1
 [ "$(dd if="/dev/$d" bs=1048576 count=4 2>/dev/null | t95h_hash)" = "$T95H_PREFIX" ] || return 1
}
platform_check_image() {
 [ "$#" = 1 ] || return 1
 # procd calls this synchronously while its watchdog event loop is blocked.
 # Validate compressed bytes here; decompress only in the RAM stage child,
 # where upgraded's parent event loop continues servicing the watchdog.
 t95h_validate_archive "$1" || { t95h_error 'Paket/Prüfsummen ungültig'; return 1; }
 t95h_manifest "$1" && t95h_target || { t95h_error 'Board, SD, Bootloader oder Layout passt nicht'; return 1; }
 echo 'T95H: Archiv und laufende SD geprüft; vollständige Rohdatenprüfung folgt im RAM.'
}
platform_pre_upgrade() {
 # Check the exact compressed payload again; full raw validation follows in RAM
 # immediately before writing. Do not decompress another time during shutdown.
 t95h_validate_archive "$1" && t95h_manifest "$1" && t95h_target || exit 1
 echo 'T95H: Archiv erneut geprüft; wechsle für die abschließende Prüfung ins RAM.' >&2
 printf '%s\n' "$T95H_DISK" > /tmp/t95h-upgrade-disk
 # Release the FAT mount before switching root. Never force a busy filesystem.
 if awk '$2=="/boot" {found=1} END {exit !found}' /proc/mounts; then
 umount /boot || exit 1
 fi
}
# Separate byte-copy primitive permits destructive-path testing on regular files.
# The platform entry point below performs all SD / mount / image checks first.
t95h_write_payload() (
 set -o pipefail
 local image="$1" rootdev="$2" bootdev="$3" member part expected count device
 t95h_manifest "$image" || exit 1
 for member in root boot; do
 if [ "$member" = root ]; then part=2; expected="$T95H_ROOT_RAW"; count=1932; else part=1; expected="$T95H_BOOT_RAW"; count=64; fi
 if [ "$part" = 2 ]; then device="$rootdev"; else device="$bootdev"; fi
 t95h_progress "$member-write START"
 t95h_stream "$image" "$member.gz" | gzip -dc | t95h_meter "$member-write" | dd of="$device" bs=1048576 iflag=fullblock oflag=direct conv=fsync || { t95h_error "$member write/flush failed"; exit 1; }
 t95h_progress "$member-write flushed; readback START"
 # Direct read bypasses the page cache after flush.
 local actual
 actual="$(dd if="$device" bs=1048576 count="$count" iflag=direct | t95h_meter "$member-readback" | t95h_hash)" || { t95h_error "$member readback I/O failed"; exit 1; }
 [ "$actual" = "$expected" ] || { t95h_error "$member readback expected=$expected actual=$actual"; exit 1; }
 t95h_progress "$member-readback VERIFIED"
 done
)
t95h_write_partitions() (
 set -o pipefail
 local image="$1" disk="$2" member part expected count
 # Revalidate before first write; also protects direct stage2 invocation.
 t95h_validate_payload "$image" && t95h_manifest "$image" && t95h_target_check "$disk" || exit 1
 # Writing is only permitted after OpenWrt has pivoted into its RAM root.
 [ "$(awk '$5=="/" {for(i=1;i<=NF;i++) if($i=="-") print $(i+1)}' /proc/self/mountinfo)" = tmpfs ] || exit 1
 local majmin
 for part in 1 2; do
 majmin="$(cat /sys/class/block/${disk}p$part/dev)" || exit 1
 awk -v d="$majmin" '$3==d {found=1} END {exit !found}' /proc/self/mountinfo && exit 1
 done
 # Both partitions must be unmounted, including old-root nested mounts.
 for member in /proc/mounts /proc/self/mountinfo; do
 grep -q "/dev/${disk}p[12] " "$member" && exit 1
 done
 t95h_backup_check || exit 1
 t95h_write_payload "$image" "/dev/${disk}p2" "/dev/${disk}p1" || exit 1
 t95h_target_check "$disk" || exit 1
 t95h_progress "ROOT-MOUNT START"
 mkdir -p /tmp/t95h-newroot
 mount -t ext4 -o rw,noatime "/dev/${disk}p2" /tmp/t95h-newroot || { t95h_error "root mount/unmount/directory failed"; exit 1; }
 trap 'umount /tmp/t95h-newroot 2>/dev/null || true' EXIT
 t95h_progress "ROOT-MOUNT OK"
 local restored=0
 if [ -n "$UPGRADE_BACKUP" ]; then
 [ -f "$UPGRADE_BACKUP" ] || { t95h_error 'CONFIG backup vanished'; exit 1; }
 [ "$(sha256sum "$UPGRADE_BACKUP" | cut -d ' ' -f 1)" = "$(cat /tmp/t95h-config-sha256)" ] || { t95h_error 'CONFIG backup changed'; exit 1; }
 t95h_progress 'CONFIG-RESTORE START'
 tar -xzf "$UPGRADE_BACKUP" -C /tmp/t95h-newroot || { t95h_error "CONFIG restore failed"; exit 1; }
 t95h_progress "CONFIG-RESTORE OK"
 restored=1
 fi
 # This receipt proves partition readback and config restore, not reboot success.
 t95h_progress "ROOT-MOUNT START"
 mkdir -p /tmp/t95h-newroot/usr/share/t95h || exit 1
 t95h_progress "RECEIPT START"
 local package_sha
 package_sha="$(sha256sum "$image" | cut -d ' ' -f 1)" || exit 1
 {
 printf 'format=T95H-UPGRADE-RECEIPT-1\npackage_sha256=%s\n' "$package_sha"
 printf 'boot_sha256=%s\nrootfs_sha256=%s\n' "$T95H_BOOT_RAW" "$T95H_ROOT_RAW"
 printf 'partition_readback_verified=1\nconfig_restored=%s\nreboot_verified=0\n' "$restored"
 } > /tmp/t95h-newroot/usr/share/t95h/last-sysupgrade || exit 1
 sync
 umount /tmp/t95h-newroot || { t95h_error "root mount/unmount/directory failed"; exit 1; }
 t95h_target_check "$disk" || exit 1
 t95h_progress 'UPGRADE-COMPLETE: readback and receipt verified; reboot pending'
)
platform_do_upgrade() {
 local disk="$(cat /tmp/t95h-upgrade-disk)"
 t95h_progress "RAM-STAGE START"
 # Stop do_stage2's success path on failure. The parent upgraded process may
 # still reboot after this exits; a reboot alone never proves upgrade success.
 t95h_write_partitions "$1" "$disk" || { t95h_error 'ABBRUCH: Upgrade unvollständig. SD-Sicherung am ThinkPad wiederherstellen.'; exit 1; }
}
