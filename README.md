# T95H Linux / OpenWrt

Experimentelles Build-Projekt für die T95H mit H616. Linux 7.2.3,
Board-Patches und die getestete Bootkette bleiben festgelegt. Jeder neue Auftrag
ermittelt die aktuelle stabile OpenWrt-Version einmal und baut genau ein Profil.
Kein A/B-Vergleichsbuild und keine automatischen Hardwaretests.

## Einstieg über installer.sh

Voraussetzungen auf dem ThinkPad: `git`, `gh`, `python3` und `gh auth login`
mit Berechtigung zum Workflow-Start. Das Repository ist öffentlich.
Authentifizierter Download als Alternative zu wget:

```sh
gh api -H 'Accept: application/vnd.github.raw+json' repos/frogro/t95h-linux/contents/installer.sh?ref=main > installer.sh
sh installer.sh
```

Direkter Download:

```sh
wget -O installer.sh https://raw.githubusercontent.com/frogro/t95h-linux/main/installer.sh
sh installer.sh
```

Das Skript legt einen separaten Checkout unter `~/.local/share/t95h-installer`
an, fragt Profil und Konsole ab und startet den vollständigen Actions-Build.
Vorhandene lokale Änderungen werden nicht überschrieben. Es flasht kein Gerät.
Ohne Dialog und für spätere Downloads:

```sh
sh installer.sh dispatch --profile base-A-B --console dual
sh installer.sh status
sh installer.sh releases
sh installer.sh release-download --tag t95h-RUN_ID-ATTEMPT
```

Ein erfolgreicher Build veröffentlicht ein experimentelles
Prerelease mit Installationsimage, Sysupgrade, Prüfsummen, Manifesten und diesem
Einstiegsskript. Das Release bleibt während des Uploads als Entwurf verborgen.
Download und Prüfsummenprüfung laufen über `gh`; ein Prerelease ist keine
Bestätigung vollständiger Hardwarestabilität.

## Gesamten Speicher nutzen

[SD-/eMMC-Restkapazität als Datenbereich verwenden](docs/storage-capacity.md):
Layout, Geräteerkennung und Einbindung unter OpenWrt. **Im aktuellen Release
verhindern Änderungen an der Partitionstabelle das Sysupgrade.** Eine automatisch
erweiterte, updatefähige Datenpartition ist noch nicht implementiert.

## eMMC-Installation direkt an der Box (experimentell)

Die neue Build-Kette erzeugt pro Profil vier Ausgaben:

- **SD-Image:** OpenWrt dauerhaft von SD verwenden.
- **eMMC-Installations-SD:** OpenWrt von SD starten; eine zusätzliche Partition
  enthält das passende eMMC-Abbild und dessen Prüfdaten. Die Installation lässt
  sich ohne Internet, ThinkPad-Verbindung oder SSH-Sitzung an der Box starten.

Zusätzlich gibt es getrennte `…-sd-sysupgrade.bin` und `…-emmc-sysupgrade.bin`.
Die Installations-SD wird als `…-sd-emmc-installer.img.gz` ausgeliefert: vor dem
Schreiben mit `gzip -dk DATEI.img.gz` entpacken. Die enthaltene eMMC-Paketprüfung
ist offline möglich. Nur das experimentelle Image mit dritter Partition enthält
den Installationsbefehl; das gewöhnliche SD-Image enthält ihn nicht.

Die eMMC-Installations-SD booten, eine USB-Tastatur anschließen und an der
HDMI-Konsole als `root` anmelden. Der Befehl lautet:

```sh
t95h-install-emmc
```

**Hardwaretest ausstehend:** Der neue Installer und eMMC-Sysupgrade sind
experimentell. Frühere Releases mit nur zwei Dateien enthalten diesen Installer
nicht. Softwareprüfungen ersetzen keinen Installationstest auf der Box.

Vor dem ersten Schreibzugriff zeigt das Skript:

> **ACHTUNG: Das vorhandene Betriebssystem auf der eMMC und alle dort
> gespeicherten Daten werden gelöscht und durch OpenWrt ersetzt.**
> Die aktuellen OpenWrt-Zugangseinstellungen der gestarteten SD werden übernommen.
> Zum Bestätigen `EMMC LOESCHEN` eingeben. Jede andere Eingabe bricht ab.

Das bloße Booten der Installations-SD löscht nichts. Nach bestätigter Installation
und erfolgreicher Abschlussprüfung die Box herunterfahren, Strom trennen,
SD entfernen und wieder einschalten.

### Einstellungen übernehmen

Der Installer übernimmt die Einstellungen des **laufenden OpenWrt auf der SD**: Root-Passwort, SSH-Konfiguration einschließlich vorhandener Hostkeys
und autorisierter Schlüssel, Netzwerk-/AP-Einstellungen und LuCI-Zugang.
Damit bleiben die bisherigen Zugangsdaten und die SSH-Identität der Box erhalten.
Android-Einstellungen werden nicht übernommen. Bestehende feste IP-Adressen
bleiben erhalten; bei DHCP kann der Router eine andere Adresse vergeben.

Die Übernahme erfolgt lokal auf dem Gerät; persönliche Passwörter und Schlüssel
gehören nicht in öffentliche Release-Images. Speicherabhängige Einstellungen wie
Root- und Boot-UUIDs, Mount-Ziele und Bootskripte müssen auf eMMC angepasst werden,
statt die SD-Konfiguration ungeprüft zu kopieren. Der Installer prüft die
Konfigurationsübernahme, bevor er Erfolg meldet.

Vor dem Schreiben sind Board, tatsächlich auf SD liegendes Root-Dateisystem,
eMMC-Identität, Größe, ausgehängte Zielpartitionen und Paketprüfsummen zu prüfen.
Eine SD, die bereits zur eMMC weiterleitet, ist kein geeignetes Installationssystem.
SD- und eMMC-Sysupgrade-Dateien bleiben getrennt und dürfen nicht verwechselt werden.
[Technischer eMMC-Stand](docs/emmc-installation.md).

## Vollständiger Build vom ThinkPad

Im Repository ausführen:

```sh
python3 installer/t95h.py dispatch --profile base-A-B --console dual
python3 installer/t95h.py status
python3 installer/t95h.py download --run-id RUN_ID --profile base-A-B --console dual
```

`dispatch` startet **Build T95H install image and sysupgrade**. Der Workflow lädt
prüfsummengesperrte Eingaben, kompiliert Kernel und passende Module, installiert
frische OpenWrt-Pakete und erzeugt Installationsimage und Sysupgrade samt
Prüfsummen und Prüfberichten. Er flasht kein Gerät und veröffentlicht keine
Hardware-Stabilitätsfreigabe. Ein erfolgreicher kompletter Actions-Lauf ist der
Nachweis der CI-Build-Kette; reine Vorbereitungs-Checks sind kein Image-Build.

Profile: `base`, `base-A`, `base-B`, `base-A-B`. Basis enthält HDMI-Konsole und
Audio, Ethernet, internes WLAN, IR und Frontdisplay. A ergänzt die ausgewählten
USB-Netzwerk-/Modemtreiber; B GPU/Multimedia einschließlich Cedrus/UVC.
PCIe, MHI und NVMe bleiben ausgeschlossen. Konsolen: `dual`, `hdmi`, `uart`.
Die konkreten Pakete/Module stehen in den Artefakt-Manifesten.

Der lokale Einstieg zur gleichen Kette ist `tools/build-openwrt-release.py`.
Die getrennten Vorbereitungs- und Quellprüfungsworkflows bleiben verfügbar.
[Build-Eingaben, Signierung und Grenzen](docs/actions-build.md).

## Standardzugang

AP **openwrt**, WLAN-Passwort **openwrtopenwrt**; SSH/LuCI **root / openwrt**.
WLAN-Adresse **192.168.50.1**, Ethernet per DHCP. Nach Installation ändern.
`python3 installer/t95h.py access` bereitet eigene Zugangsdaten lokal vor;
es überträgt diese nicht automatisch als GitHub-Build-Eingabe.
[Zugangsregeln](docs/default-access.md).

## Dokumentierte Hardwarepunkte

SD-Start: eine Sekunde Wartezeit und bis zu drei MMC-Rescan-/Ladeversuche im
Bootskript; bisher zwei erfolgreiche Kaltstarts auf den ersten Versuch gemeldet.
Keine gezielte Stromschaltung, keine Bootmarker und kein Beweis vollständiger
Kaltstartzuverlässigkeit. Das Skript hilft erst, nachdem es geladen wurde.
WLAN: konsolidierter xradio-Stand mit vier u32-Leselängenkorrekturen und Firmware
.58; gelegentliche SDIO-Datenfehler/missed interrupts bleiben dokumentiert.
GPU-Initialisierung und Audio-Hardwarevalidierung bleiben ebenfalls offene
Punkte. Weitere Hör-, Belastungs- oder Hardwaretests sind derzeit nicht Teil
dieses Auftrags. Andere Linux-Distributionen werden später konkret angepasst.

## Erfolgreicher vollständiger Actions-Lauf

Der [Lauf 34363631215](https://github.com/frogro/t95h-linux/actions/runs/34363631215)
hat Basis+A+B mit dualer Konsole vollständig gebaut. Download, Image-Prüfsummen,
Kernel-APK-Signatur und das enthaltene SD-Rescan-Skript wurden anschließend auf
dem ThinkPad geprüft. [Prüfnachweis](docs/actions-validation-20260909.md).

## Weiteres Betriebssystem: LibreELEC

[Experimenteller LibreELEC-Port](docs/libreelec.md), zunächst Basis+B.
Ein eigener Actions-Workflow ermittelt pro Lauf die neueste stabile Version.
Die ersten Ausgaben sind Testartefakte, noch keine hardwaregeprüften Releases.

## USB-Anschlüsse

Beide USB-Buchsen arbeiten als Host, einschließlich USB0 neben dem SD-Kartenschacht.
USB0 wurde mit dem RTL8821CU-Stick erfolgreich auf Erkennung und WLAN-Scans
in beiden Frequenzbändern getestet. Weitere Geräte benötigen ihre jeweiligen
Profil-Treiber; deren Betrieb und Strombedarf sind gerätespezifisch zu prüfen.
