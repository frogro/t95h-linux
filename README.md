# Deine T95H kann mehr

**OpenWrt, LibreELEC und AnotterKiosk wurden für die T95H mit Allwinner H616 portiert.**
Dieses Repository veröffentlicht die passenden Images: herunterladen, auf SD
schreiben und die Box als Netzwerkgerät, Mediacenter oder Kiosk nutzen.

**[→ Images herunterladen](https://github.com/frogro/t95h-linux/releases)** ·
[Installation auf SD](#image-herunterladen-und-auf-sd-schreiben)

## Welches System passt zu dir?

| System | Dafür ist es da |
| --- | --- |
| [OpenWrt](#openwrt--netzwerk-und-router) | Netzwerk, Router und Access Point mit Weboberfläche. Je nach Profil kommen USB-Netzwerkgeräte, Modems und Multimedia-Treiber hinzu. |
| [Kodi / LibreELEC](#kodi--libreelec--das-mediacenter) | Filme, Musik und andere Medien am Fernseher. LibreELEC startet direkt die Kodi-Oberfläche. |
| [AnotterKiosk](#anotterkiosk--webseiten-und-bildschirmübertragung) | Eine Webseite im Vollbild: etwa Dashboard, Haussteuerung oder Infotafel. Mit zusätzlicher Bildschirmübertragung lässt sich auch ein PC auf der Box anzeigen und optional bedienen. |

Nicht jedes Release enthält alle Systeme oder Varianten. Die Releasebeschreibung
nennt die enthaltene Version, Änderungen und Hinweise zur jeweiligen T95H-Hardware.
Bitte ausschließlich die Images für **T95H/H616** verwenden.

## Image herunterladen und auf SD schreiben

1. Unter **Releases → Assets** das gewünschte T95H-Image herunterladen.
   Für den Start von SD eine Datei mit `sd` beziehungsweise `install.img` im
   Namen wählen. Eine `sysupgrade.bin` ist nur zum Aktualisieren von OpenWrt.
2. Eine Datei mit `.img.gz` entpacken, sodass eine `.img` entsteht. Unter Linux
   geht das mit `gzip -dk DATEINAME.img.gz`, unter Windows etwa mit 7-Zip.
   Falls vorhanden, die heruntergeladene Datei mit `SHA256SUMS` vergleichen.
3. SD-Karte am Computer anschließen. Für AnotterKiosk mindestens **8 GB**
   verwenden; für andere Images die Mindestgröße im Release beachten.
4. In einem Image-Schreibprogramm, beispielsweise Raspberry Pi Imager mit
   **eigenem Image** oder balenaEtcher, die `.img` und die richtige SD-Karte
   auswählen und schreiben. **Dabei wird der gesamte Inhalt der SD gelöscht.**
   Keine Raspberry-Pi-spezifischen Anpassungen von Benutzer, WLAN oder SSH anwenden.
   Unter Linux bietet auch „Laufwerke“ die Funktion „Laufwerksabbild wiederherstellen“.
5. Nach dem Schreiben die SD sicher entfernen. Für AnotterKiosk zuvor die
   unten beschriebene Konfiguration auf der SD anpassen.
6. Box stromlos machen, SD einsetzen, HDMI und Ethernet anschließen und einschalten.
   Der erste Start kann länger dauern. Die Netzwerkadresse steht im Router.

Das Image muss auf die **ganze SD-Karte** geschrieben werden. Die `.img` nur als
Datei auf die Karte zu kopieren reicht nicht. Ein getrenntes Formatieren vorher
ist nicht erforderlich.

## OpenWrt – Netzwerk und Router

OpenWrt bietet eine Weboberfläche (LuCI), SSH und Netzwerkfunktionen.
Welche zusätzlichen Treiber enthalten sind, steht im Profil des Releases:

| Profil | Enthalten |
| --- | --- |
| `base` | Grundsystem, Ethernet, internes WLAN sowie Unterstützung für HDMI-Konsole, Audio, IR und Frontdisplay |
| `base-A` | Grundsystem plus ausgewählte USB-Netzwerk- und Modemtreiber |
| `base-B` | Grundsystem plus GPU-/Multimedia-Unterstützung und USB-Video (UVC) |
| `base-A-B` | Beide Erweiterungen zusammen |

Enthaltene Treiber bedeuten nicht, dass jedes angeschlossene Gerät getestet wurde.
Beide USB-Buchsen sind Hostanschlüsse. Bei älteren Releases können Umfang und
Dateinamen abweichen; maßgeblich ist deren Releasebeschreibung. Die OpenWrt-Version
steht im Dateinamen, das Profil bezeichnet den Funktionsumfang.

**Standardzugang:** WLAN `openwrt`, WLAN-Passwort `openwrtopenwrt`;
SSH und LuCI: Benutzer `root`, Passwort `openwrt`.
Über WLAN ist die Box unter `192.168.50.1` erreichbar, über Ethernet erhält sie
normalerweise eine Adresse vom Router. Die Standardpasswörter nach dem Start ändern.

### SD oder eMMC?

| Datei im Release | Verwendung |
| --- | --- |
| `…-sd-install.img` | OpenWrt dauerhaft von SD starten |
| `…-sd-emmc-installer.img.gz` | Von SD starten und OpenWrt anschließend auf den internen eMMC-Speicher installieren |
| `…-sd-sysupgrade.bin` | Ein vorhandenes OpenWrt auf SD aktualisieren |
| `…-emmc-sysupgrade.bin` | Ein vorhandenes OpenWrt auf eMMC aktualisieren |

Für eMMC zuerst die **eMMC-Installations-SD** starten. Dann an der HDMI-Konsole
mit USB-Tastatur oder per SSH anmelden und ausführen:

```sh
t95h-install-emmc
```

**Achtung: Das vorhandene Betriebssystem und alle Daten auf der eMMC werden
bei Bestätigung gelöscht.** Das bloße Starten der SD löscht noch nichts.
Der Befehl fragt ausdrücklich nach `EMMC LOESCHEN`.
Die aktuellen OpenWrt-Zugangseinstellungen der SD werden übernommen, darunter
Passwort, SSH-Schlüssel und Netzwerk-/WLAN-Konfiguration.
Nach erfolgreicher Installation herunterfahren, Strom trennen, SD entfernen
und wieder einschalten. [Weitere Informationen](docs/emmc-installation.md).

### Updates

OpenWrt ist über die zum Release gehörende **Sysupgrade-Datei updatefähig**.
Vorher die Konfiguration sichern. Die passende SD- oder eMMC-Datei unter
**System → Backup / Firmware aktualisieren** in LuCI auswählen und die
Einstellungen bei Bedarf beibehalten. Ablehnungen nicht mit „Force“ umgehen.
Eine `.img` neu zu flashen ist eine Neuinstallation.

Die ursprüngliche Partitionierung muss erhalten bleiben; selbst vergrößerte
oder zusätzliche Partitionen können die Updateprüfung scheitern lassen.
Updates ersetzen nicht automatisch den Bootloader. Einschränkungen und den
Teststand jeweils in der Releasebeschreibung beachten.

## Kodi / LibreELEC – das Mediacenter

LibreELEC macht die Box zum Kodi-Mediacenter am Fernseher. Über Kodi lassen sich
Medienbibliotheken, Netzwerkquellen und passende Add-ons nutzen.

Das normale SD-Image startet direkt von SD. Eine Datei mit
`sd-emmc-installer` im Namen ermöglicht zusätzlich die
[Installation auf den internen eMMC-Speicher](docs/media-emmc-installation.md).
Das rohe eMMC-Image allein ist keine Installations-SD.

Den jeweiligen Download und Teststand findest du unter
[Releases](https://github.com/frogro/t95h-linux/releases).
Ein eigener T95H-Updateweg wird noch nicht angeboten; OpenWrt-Updatedateien
sind hier nicht verwendbar. [Weitere Informationen zu LibreELEC](docs/libreelec.md).

## AnotterKiosk – Webseiten und Bildschirmübertragung

AnotterKiosk startet automatisch einen Browser und zeigt die eingestellte
Webseite im Vollbild, etwa ein Dashboard, eine Haussteuerung oder eine lokale
Infoseite. Die Inhalte und die Bedienoberfläche liefert die Webseite.
Die ursprüngliche Startseite kann zunächst erscheinen; sie muss für eine eigene
Anzeige durch die gewünschte Adresse ersetzt werden.

Nach dem Flashen die SD erneut am Computer einstecken und auf der Partition
**T95HKIOSK** die Datei **`kioskbrowser.ini`** mit einem Texteditor öffnen.
Im vorhandenen Abschnitt `[browser]` die Zeile `url` ändern:

```ini
[browser]
url="http://mein-server/meine-seite/"
```

Speichern, SD sicher entfernen und die Box starten. Für diesen Port zunächst
Ethernet verwenden. Die Webseite muss von der Box aus erreichbar sein.
Die INI-Datei bietet außerdem Einstellungen für Auflösung, Sprache und weitere
Kiosk-Funktionen. Eigene lokale Webseiten lassen sich auf der Bootpartition
unter `www-public` ablegen.

SSH wird wie im Original über eine Datei **`authorized_keys`** auf dieser
Partition eingerichtet. Dort den **öffentlichen** SSH-Schlüssel des eigenen
Computers eintragen. Es gibt kein vorgegebenes SSH-Passwort.
[Konfiguration, SSH und Änderungen im laufenden Betrieb](docs/anotter-kiosk.md).

Je nach Release gibt es ein SD-Image und eine SD mit zusätzlichem eMMC-Installer.
[AnotterKiosk auf eMMC installieren](docs/media-emmc-installation.md).
Ein Update ohne erneutes Flashen wird hier noch nicht angeboten.

### Bildschirmübertragung und optionale Fernsteuerung

Ein anderer Computer kann seinen Bildschirm im lokalen Netzwerk bereitstellen.
Mit Deskreen CE trägt man dessen Verbindungsadresse als Kiosk-URL ein und gibt
den Bildschirm auf dem sendenden Computer frei. Eine neue Sitzung kann eine
neue Adresse erfordern. Eine externe Cloud ist für diesen Aufbau nicht nötig.

Im T95H-Test war **go2rtc mit direkter Cedrus-Videoausgabe** deutlich besser
bedienbar als Deskreen im Browser. Das ist ein zusätzlicher nativer
Player und noch keine fertige Funktion der Kiosk-Webseite. Der getestete
Aufbau und seine Grenzen stehen in der [Anleitung zur Bildschirmübertragung](docs/screen-sharing.md).

Optional kann **VirtualHere** Maus und Tastatur an der Box als USB-Geräte an
den sendenden Computer weiterreichen. Währenddessen bedienen sie den entfernten
Computer; für lokale Dialoge an der Box muss man den Empfänger wieder freigeben.
VirtualHere ist separate Software mit eigenen Lizenzbedingungen und wird nicht
mit dem Image ausgeliefert.

## Weitere Informationen

[Anotter-Konfiguration](docs/anotter-kiosk.md) ·
[Bildschirmübertragung](docs/screen-sharing.md) ·
[LibreELEC](docs/libreelec.md) ·
[Technische Build-Dokumentation](docs/actions-build.md)
