# AnotterKiosk und LibreELEC auf eMMC installieren

Das Release muss eine Datei **`…-sd-emmc-installer.img.gz`** enthalten.
Das normale SD-Image und das rohe `…-emmc.img.gz` sind dafür nicht austauschbar.
Für die Installations-SD empfehlen wir mindestens **16 GB**; das Manifest gibt
die tatsächliche entpackte Größe an. Die eMMC muss das enthaltene Zielimage fassen.

1. Die Installations-SD wie in der README beschrieben schreiben.
2. Die Box von dieser SD starten und das System einrichten. Bei AnotterKiosk
   zuvor `authorized_keys` und `kioskbrowser.ini` auf der SD bearbeiten.
3. Als root anmelden. Anotter verwendet SSH-Schlüssel; bei LibreELEC SSH in dessen
   Einrichtung aktivieren und die dort eingerichteten Zugangsdaten verwenden.
4. Die zusätzliche Installationspartition einhängen und das Skript starten:

```sh
mkdir -p /tmp/t95h-install
mount -o ro,exec /dev/disk/by-label/T95HINSTALL /tmp/t95h-install
sh /tmp/t95h-install/install-emmc.sh
```

Falls die Partition bereits automatisch eingehängt wurde, deren Mountpunkt
verwenden und dort `sh install-emmc.sh` ausführen. Das Skript muss direkt aus
der dritten Partition derselben gestarteten SD laufen; es prüft das vor dem Schreiben.

**ACHTUNG: Das vorhandene Betriebssystem und alle Daten auf der eMMC werden
gelöscht.** Das Skript zeigt Ziel und Größe an und verlangt ausdrücklich
`EMMC LOESCHEN`. Das Booten der Installations-SD allein schreibt nichts auf eMMC.
Keine Gerätenamen wie `/dev/mmcblk0` auf Verdacht als Schreibziel verwenden.

Die Einstellungen werden von der gestarteten SD übernommen:

| System | Übernahme |
| --- | --- |
| AnotterKiosk | `kioskbrowser.ini`, SSH-Schlüsseldateien auf der Bootpartition, Startbild und `www-public` |
| LibreELEC | `.config`, `.cache` und `.kodi` aus `/storage`, darunter Netzwerk-, SSH- und Kodi-Einstellungen |

Größere eigene Medienbestände werden nicht mitkopiert. Bei zu großen Einstellungen
bricht der Installer vor dem Schreiben ab. Die neue Partitionierung und die
passenden Bootkennungen stammen aus dem eMMC-Image, nicht aus den SD-Einstellungen.

Nach **PASS**: `poweroff`, Strom trennen, SD entfernen und wieder einschalten.
Bei einem Fehler nicht von einer erfolgreichen Installation ausgehen. Der
Installer verändert die gestartete SD nicht. Ein erneutes Schreiben eines
Images ist eine Neuinstallation und kein Update.

## Teststand dieses Adapters

Die eMMC-Bootprefix- und Controller-Anpassungen stammen aus den vorhandenen
T95H-Tests. Die neuen Anotter-/LibreELEC-Installationswege sind vorerst
Release-Kandidaten und müssen jeweils auf der Box getestet werden. Insbesondere
ersetzt ein OpenWrt-eMMC-Test nicht den Bootnachweis für diese beiden Systeme.
RPMB und interner Controller-Speicher werden nicht als gelöscht ausgegeben.
