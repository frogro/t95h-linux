# Eigenständige Rootfs-Erzeugung

`tools/assemble-openwrt-packages.py` installiert signierte APKs in einen **leeren**
Ordner. Eingaben: aufgelöster Buildauftrag, passender OpenWrt-ImageBuilder,
öffentliche Prüfschlüssel und tatsächlich gebautes T95H-Kernelpaket samt SHA256.
Kein Gerätebackup und kein Vorgängerimage werden verwendet. Das Tool führt keine
Paket- oder Android-Programme aus; OpenWrt-Postinstall ist eine eigene Folgestufe.

Die Seeds stammen aus `boards/t95h/openwrt/packages.json`, abhängig vom Profil.
Die Dependencies werden gegen genau die OpenWrt-Version des Auftrags aufgelöst.
Die Paketdatenbank wird anschließend auf fremde `kernel`-/`kmod-*`-Pakete geprüft.
Der Custom-Kernel muss deren benötigte Funktionen tatsächlich enthalten und
bereitstellen; ein vorgetäuschter Provider ist kein Ersatz.

Ergebnisse: `root/`, `packages.log`, `package-lock.json`, verwendete öffentliche
Schlüssel und Feedliste. Der Lock erfasst die aufgelösten Paketversionen. Für
spätere Offline-Reproduktion müssen auch die APK-Dateien und ihre Prüfsummen
archiviert werden; ein Versionslock allein schützt nicht vor verschwundenen Feeds.

## Lokaler Entwicklungsnachweis

Am 09.09.2026 wurde Basis+A+B mit 252 Paketen erfolgreich frisch installiert.
Das vorhandene `7.2.3-r8`-Kernelpaket diente nur zum Test der Paketstufe. Es
enthält noch nicht den neuen konservativen Quellstand einschließlich u32-Fix.
Dieser Testordner ist weder Release-Artefakt noch ein bootfertiges Rootfs.

Auch `tools/prepare-openwrt-rootfs.py` wurde lokal erfolgreich ausgeführt:
OpenWrt-Postinstall, gesperrte Boarddienste, Standard-Rootzugang und kompilierte
Display-/Upgrade-Helfer sind in einer neuen Kopie vorbereitet. Persönliche
Geräteschlüssel werden nicht übernommen. Der Bericht markiert diesen Stand
weiterhin ausdrücklich als nicht bootfertiges Entwicklungsartefakt.

## Noch zu verbinden

- Abschließende Prüfung der Dienstabhängigkeiten und Profil-Vollständigkeit.
- Gesperrte T95H-Runtime, profilgerechte Firmware und externe Module.
- Lokale Konfigurationsdateien auf der Ziel-SD mit 0600; Git speichert nur das
  Executable-Bit, nicht solche vollständigen Dateirechte.
- Öffentliches Root-Standardpasswort initialisieren, persönliche Schlüssel
  ausschließen; optionale lokale Erstkonfiguration erst beim Flashen einsetzen.
- GPU-Startbereitschaft mit bewusst deaktiviertem AP: der bisherige Dienst
  erwartet aktives internes WLAN. Dies muss vor Freigabe der Kombination
  Profil B / kein AP berücksichtigt werden.
- Bootkette, FAT/ext4 und Installations-/Sysupgrade-Paar aus demselben Auftrag.

Der alte Zusatztreiber und der bewährte Bootunterbau bleiben gesperrt, bis ihre
Quellen, Abhängigkeiten und Signieranforderungen vollständig eingebunden sind.
