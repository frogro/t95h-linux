#!/bin/sh
# ThinkPad/Linux bootstrap. No disk writes and no automatic flashing.
set -eu
REPO=frogro/t95h-linux
for tool in git gh python3; do
 command -v "$tool" >/dev/null 2>&1 || { echo "Fehlt: $tool. Unter Ubuntu: sudo apt install git gh python3" >&2; exit 1; }
done
gh auth status >/dev/null 2>&1 || { echo 'Bitte zuerst: gh auth login' >&2; exit 1; }
checkout=${T95H_INSTALLER_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/t95h-installer}
if [ -e "$checkout" ]; then
 [ -d "$checkout/.git" ] || { echo "Kein Git-Checkout: $checkout" >&2; exit 1; }
 case "$(git -C "$checkout" remote get-url origin)" in
  https://github.com/frogro/t95h-linux|https://github.com/frogro/t95h-linux.git|git@github.com:frogro/t95h-linux.git) ;;
  *) echo 'Unerwartetes Repository; nichts aktualisiert.' >&2; exit 1;;
 esac
 [ -z "$(git -C "$checkout" status --porcelain)" ] || { echo 'Lokale Änderungen vorhanden; nichts aktualisiert.' >&2; exit 1; }
 [ "$(git -C "$checkout" branch --show-current)" = main ] || { echo 'Checkout ist nicht auf main.' >&2; exit 1; }
 git -C "$checkout" fetch origin main
 git -C "$checkout" merge --ff-only origin/main
else
 mkdir -p "$(dirname "$checkout")"
 gh repo clone "$REPO" "$checkout" -- --branch main --single-branch
fi
if [ "$#" -eq 0 ]; then
 [ -t 0 ] || { echo 'Ohne Terminal: installer.sh dispatch --profile base-A-B --console dual' >&2; exit 1; }
 printf 'Profil [base / base-A / base-B / base-A-B] (base-A-B): '
 read -r profile
 profile=${profile:-base-A-B}
 case "$profile" in base|base-A|base-B|base-A-B) ;; *) echo 'Ungültiges Profil' >&2; exit 1;; esac
 printf 'Konsole [dual / hdmi / uart] (dual): '
 read -r console
 console=${console:-dual}
 case "$console" in dual|hdmi|uart) ;; *) echo 'Ungültige Konsole' >&2; exit 1;; esac
 set -- dispatch --profile "$profile" --console "$console"
fi
exec python3 "$checkout/installer/t95h.py" "$@"
