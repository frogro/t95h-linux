# Deine T95H kann mehr

Nutze deine **T95H mit Allwinner H616** als Router, Mediacenter oder
Web-Anzeige. Wähle ein System, schreibe es auf eine SD-Karte und starte die Box.

**[→ Images herunterladen](https://github.com/frogro/t95h-linux/releases)**

## Welches System passt zu dir?

| System | Was du damit machen kannst |
| --- | --- |
| **OpenWrt** | Netzwerk und WLAN verwalten, einen Access Point einrichten und USB-Netzwerkgeräte nutzen. Mit Multimedia-Anwendungen auch Video aufnehmen oder streamen. |
| **LibreELEC / Kodi** | Filme, Musik und Medien aus deinem Netzwerk am Fernseher abspielen. Die Box startet direkt mit Kodi. |
| **AnotterKiosk** | Eine Webseite im Vollbild anzeigen, etwa eine Haussteuerung oder Infotafel. Auch der Bildschirm eines anderen Computers lässt sich anzeigen. |

## Image herunterladen und auf SD schreiben

1. **Herunterladen:** Öffne oben „Images herunterladen“. Wähle dein System
   und klappe beim passenden Release **Assets** auf. Lade das SD-Image herunter:
   eine Datei mit `-sd.img.gz` oder bei OpenWrt `-sdcard-install.img.gz` am Ende.
   Möchtest du später auf den internen Speicher wechseln, nimm stattdessen
   `-sd-emmc-installer.img.gz`.
2. **Entpacken:** Entpacke die heruntergeladene `.gz`-Datei. Du erhältst eine
   Datei mit der Endung `.img`.
3. **Auf die Karte schreiben:** Stecke eine SD-Karte in deinen Computer.
   Öffne Raspberry Pi Imager, wähle **Eigenes Image**, dann die `.img`-Datei
   und deine SD-Karte. Starte den Schreibvorgang. Zusätzliche Einstellungen
   für Raspberry Pi überspringen. **Der bisherige Inhalt der SD-Karte wird gelöscht.**
4. **Box starten:** Entferne die Karte sicher vom Computer. Setze sie in die
   ausgeschaltete T95H ein, verbinde HDMI und ein Netzwerkkabel und schalte die Box ein.
   Für AnotterKiosk kannst du vorher noch die gewünschte Webseite einstellen – siehe unten.

Verwende eine **SD-Karte mit mindestens 16 GB**. Du musst sie nicht vorher
formatieren. Die Image-Datei einfach auf die Karte zu kopieren reicht nicht;
das Schreibprogramm übernimmt die Einrichtung.

## OpenWrt – Netzwerk und Router

Verbinde die Box für die Einrichtung per Netzwerkkabel mit deinem Router.
Ihre IP-Adresse findest du dort in der Geräteliste. Öffne diese Adresse
im Browser, um die Weboberfläche **LuCI** aufzurufen.

| Zugang bei einer neuen Installation mit Kernel 6 | Vorgabe |
| --- | --- |
| Benutzer für Weboberfläche und SSH | `root` |
| Passwort | `openwrt` |
| WLAN-Name | `OpenWrt` |
| WLAN-Passwort | `openwrtopenwrt` |

Ändere die Standardpasswörter nach der Anmeldung. Wenn du bei einem Update
Einstellungen übernimmst, gelten deine bisherigen Zugangsdaten weiter.

Das **Profil** im Dateinamen bestimmt die zusätzlich installierten Programme
und Treiber:

| Profil | Umfang |
| --- | --- |
| `base` | Netzwerk-Grundsystem mit Ethernet und internem WLAN |
| `base-A` | Zusätzlich USB-Netzwerkadapter und Modems |
| `base-B` | Zusätzlich Multimedia-Anwendungen, GPU-Unterstützung und USB-Video |
| `base-A-B` | Beide Erweiterungen zusammen |

**Aktualisieren:** Sichere in LuCI deine Einstellungen und öffne
**System → Backup / Firmware aktualisieren**. Wähle die `sysupgrade`-Datei
für dein Speichermedium: `sdcard` für SD oder `emmc` für den internen Speicher.
Die Option zum Beibehalten der Einstellungen übernimmt deine Konfiguration.
Das kombinierte Installationsimage ist keine Sysupgrade-Datei.

Für ältere OpenWrt-Images gelten deren Zugangsdaten und Dateinamen.
Beim Wechsel von einem älteren Kernel-6-Image hilft die
[Anleitung zum Updateübergang](docs/boot-and-native-update-20260917.md#boot-und-updates).

## LibreELEC / Kodi – Filme und Musik

Nach dem Start führt dich Kodi durch die Einrichtung. Wähle Sprache und
Netzwerk und füge anschließend deine Medien hinzu – beispielsweise von einem
USB-Laufwerk oder einer Netzwerkfreigabe.

Die Bedienung erfolgt am Fernseher mit Tastatur, Maus oder einer kompatiblen
Fernbedienung.

## AnotterKiosk – deine Webseite am Bildschirm

AnotterKiosk öffnet nach dem Start automatisch eine Webseite im Vollbild.
So stellst du deine eigene Startseite ein:

1. Stecke die beschriebene SD-Karte noch einmal in deinen Computer.
2. Öffne auf dem Laufwerk **T95HKIOSK** die Datei **`kioskbrowser.ini`**
   mit einem Texteditor.
3. Ändere im vorhandenen Abschnitt `[browser]` die Adresse hinter `url`:

   ```ini
   [browser]
   url="http://mein-server/meine-seite/"
   ```

4. Speichere die Datei, entferne die SD sicher und starte die Box damit.

Die Webseite muss im Netzwerk der Box erreichbar sein. Für WLAN trägst du
in derselben Datei unter `[wifi]` deinen Netzwerknamen und dein Passwort ein.
Eigene lokale Webseiten kannst du auf der SD unter `www-public` ablegen.

Die [Anotter-Anleitung](docs/anotter-kiosk.md#internes-wlan) erklärt die
WLAN-Einrichtung; im selben Dokument findest du auch den SSH-Zugang.
Zum Aktualisieren gibt es eine eigene
[Anleitung für den Imagewechsel mit Einstellungserhalt](docs/anotter-image-update.md).

### Bildschirm eines anderen Computers anzeigen

Dafür gibt es zwei Wege im lokalen Netzwerk:

| Weg | So verwendest du ihn |
| --- | --- |
| **Deskreen CE im Kiosk-Browser** | Starte Deskreen auf deinem Computer. Trage die angezeigte Verbindungsadresse als Kiosk-URL ein und bestätige die Bildschirmfreigabe am Computer. |
| **go2rtc mit Cedrus-Player** | Starte die Bildschirmaufnahme und go2rtc auf deinem Computer. Verbinde dich per SSH mit der Box und starte `t95h-desktop-view`. Der Player zeigt das Video direkt über HDMI. Mit `Strg+C` kehrst du zur Kiosk-Webseite zurück. |

Die [Schritt-für-Schritt-Anleitung zur Bildschirmübertragung](docs/screen-sharing.md)
führt dich durch beide Wege. Der beschriebene go2rtc-Aufbau verwendet einen
Linux-PC mit Intel-Grafik und überträgt das Bild ohne Ton. Ein HDMI-Grabber
ist für diese beiden Wege nicht erforderlich.

Optional kannst du mit **VirtualHere** auch Maus und Tastatur an der Box zum
Bedienen des sendenden Computers verwenden. Die Einrichtung steht in derselben
Anleitung. VirtualHere wird separat installiert und hat eigene Lizenzbedingungen.

## Ohne SD-Karte starten: Installation auf eMMC

**eMMC ist der interne Speicher der Box.** Wähle beim Download das kombinierte
`-sd-emmc-installer.img.gz` und starte zunächst von dieser SD-Karte.
Die Installation auf den internen Speicher löst du anschließend selbst aus.
Das Einsetzen und Starten der SD allein löscht dort nichts.

**Bei der Installation wird das bisherige System auf der eMMC ersetzt.**
Der Installer fragt vorher nach einer Bestätigung und übernimmt die vorgesehenen
Einstellungen des SD-Systems.

Folge der [Anleitung zur eMMC-Installation](docs/media-emmc-installation.md).
Nach erfolgreichem Abschluss: Box herunterfahren, Strom trennen, SD entfernen
und wieder einschalten.
