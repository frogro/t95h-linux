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
- Profilgerechte Firmware und externe Module zum finalen Kernelpaket zusammenführen.
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

Die Rootfs-Vorbereitung ruft jetzt die eigenständige Profil-DTB-Ableitung auf
und übernimmt USB-Autoload sowie den D-Bus-Startschutz aus der frisch installierten
ModemManager-Version. Die abgeleitete ANA-Quelle muss weiterhin zusammen mit
dem passenden Kernel kompiliert werden. Der Workflow prüft alle vier DT-Profile.

## Einmaliger Profil-Kernelbuild

`tools/build-profile-kernel.py` verbindet den verifizierten Quellaufbau mit einem
Profil-Kconfig, expliziter Toolchain und den gesperrten eingebetteten Firmwaredateien.
Es lehnt veränderte Quellen/Firmware ab und prüft nach `olddefconfig`, dass keine
angeforderte y/m-Funktion verloren ging. `build-status.json` und `build.log`
werden im neuen Ausgabeordner geführt. Es gibt keinen automatischen zweiten
Vergleichsbuild und keine Installation auf der Box.

Aktuell werden Toolchain und Firmware noch als lokale geprüfte Eingaben übergeben.
Für einen vollständigen Actions-Kernelbuild fehlen deren Download-/Lizenz-Locks;
die Quellreplay-Stufe läuft bereits auf GitHub. Compiler-Identität, Compiler-SHA256,
Konfiguration und Firmwareprüfsummen stehen im Buildbericht. Dies ersetzt noch
keinen vollständigen Lock sämtlicher Toolchain-Bestandteile.

## Externe Module pro Profil

`tools/build-profile-modules.py` nimmt den abgeschlossenen Kernel-Ausgabeordner,
identische Toolchain, Epoch und einen neuen Ausgabeordner entgegen. Vor dem
Schreiben werden Kernel-/Konfigurations-/Compiler-Prüfsummen und gesperrte externe
Quellen geprüft. Der Regulatortreiber wird immer, der abgeleitete ANA-Treiber nur
für B gebaut. Alle In-Tree- und externen Module werden gemeinsam installiert;
Modulversionen und `depmod` gehören zur Prüfung. Kernel-Quellverknüpfungen werden
nicht in die Nutzdaten übernommen. Ergebnis ist ein Modul-Staging mit Bericht,
noch kein APK. Der vollständige Durchlauf wartet auf den laufenden Kernelbuild.

## Signiertes Kernelpaket

Der erste konservative Basis+A+B-Kernel und alle 35 ladbaren Module wurden am
09.09.2026 erfolgreich gebaut. `tools/package-profile-kernel.py` erzeugt daraus
mit explizitem lokalem Signierschlüssel und öffentlichen Prüfschlüsseln ein APK.
Es prüft die Kernel-/Modulprovenienz und übernimmt nur tatsächlich aktivierte
Kernel-Provider. Die Firmware wird über ihre gesperrten Prüfsummen eingebunden;
`wireless-regdb` bleibt Eigentümer der externen Regulierungsdatenbank.

Der ANA-Treiber wird nach `/usr/lib/t95h-gpu` verschoben und erhält dort die vom
späten Startdienst geprüfte Prüfsummendatei. Er darf nicht über die Modulalias-
Datenbank vorzeitig gebunden werden. Die übrigen Module verbleiben im normalen
Modulbaum; dessen Abhängigkeiten werden anschließend neu erzeugt. Der private
Signierschlüssel wird weder in das Paket noch ins Repo kopiert. APK-Signaturprüfung
ist Teil der Paketstufe. Dies ersetzt nicht die ausstehende Hardwareprüfung.

## Frisches Installationsimage

`tools/assemble-profile-image.py` erhält das geprüfte Rootfs-Staging, den explizit
geprüften Bootprefix, ImageBuilder, Epoch und Konsolenauswahl. Es erstellt FAT16
(64 MiB) und ext4 (1932 MiB) neu und behält die festgelegte Partitionstabelle,
Dateisystem-IDs und Bootkette. Die Bootskripte liegen mit Prüfsummen und lesbarem
Text im Repo. Es werden keine alten Rootfs-Partitionen übernommen.

Vor der Ausgabe werden alle regulären Rootfs-Dateien und Symlinks aus ext4 sowie
Kernel, DTB und Skripte aus FAT ausgelesen und mit den Eingaben verglichen. Die
Image-Datei wird nach dem Schreiben erneut vollständig gehasht. Dies ist eine
Dateiprüfung am ThinkPad, keine Hardware-Bootfreigabe. Das bestehende Upgrade-
Paketwerkzeug leitet anschließend das zusammengehörige Artefaktpaar daraus ab.

Für Profil B ohne aktiv konfigurierte Schnittstelle auf radio0 fordert der GPU-
Startdienst kein aktives Funknetz mehr. LAN/SSH, Abschluss des WLAN-Workers und
Versorgungsprüfungen bleiben erhalten. Die Konfigurationslogik ist mit sechs
Fällen getestet; Hardwareprüfung dieser optionalen Konfiguration steht aus.

### Image-Datei: direkter Schreib-/Lesevergleich

Bei einem lokalen Zusammenbau am 09.09.2026 wich die zusammengesetzte Image-Datei
an einem Byte innerhalb von `luci.so` vom geprüften ext4 ab. Die extrahierte Datei
im ext4 und die frisch installierte APK-Datei hatten weiterhin gleiche Prüfsummen.
Eine zweite, zunächst gemeldete Abweichung im freien Bereich war in drei direkten
Leseversuchen nicht vorhanden. Die Ursache ist offen; der Fehler wurde nicht als
Kernel- oder SSD-Defekt eingeordnet. Das fehlerhafte Image wurde nicht freigegeben.

Der Zusammensetzer verwendet jetzt `direct_image_io.py`: ausschließlich reguläre,
alignierte Dateien, O_DIRECT beim Lesen/Schreiben, exclusive neue Zieldatei,
Quellprüfsummen vor/während/nach dem Kopieren und zwei vollständige direkte
Ziel-Lesungen. Ein Fehler liefert keinen Erfolgsbericht und kein Upgrade-Artefakt.
Das ist eine Integritätsprüfung, kein Nachweis einer behobenen Hardwareursache.
