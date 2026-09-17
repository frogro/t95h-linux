# AnotterKiosk auf T95H: Imagewechsel mit Einstellungserhalt

Upstream dokumentiert das Herunterladen und Flashen eines Images:
https://github.com/Manawyrm/AnotterKiosk#how-to--installation-guide
Ein freigegebener In-place-/Auto-Updater ist dort nicht vorhanden:
https://github.com/Manawyrm/AnotterKiosk/issues/9
Unsere Hilfswerkzeuge ergänzen diesen Imagewechsel um automatischen
Einstellungserhalt für T95H. Sie sind eine T95H-Ergänzung, kein Upstream-Updater.
APT aktualisiert Debian-Pakete, ersetzt aber keinen vollständigen Imagewechsel.

## Dateien und Umfang

Ein Release enthält SD solo, die kombinierte SD mit eMMC-Installer, das darin
enthaltene eMMC-Image, manifest.json, SHA256SUMS und update-anotter-sd.py.
Für Updates werden dieselben vollständigen Images verwendet; es gibt keine
zusätzlichen Delta-Images. Der eMMC-Updatemodus liegt auf Partition 3 der
kombinierten SD. Es wird niemals automatisch beim Booten geflasht.

Automatisch erhalten bleiben die Dateien auf der bisherigen FAT-Bootpartition:

- kioskbrowser.ini (Kiosk-, Netzwerk- und weitere Anotter-Einstellungen)
- wpa_supplicant.conf (separate WLAN-Konfiguration)
- authorized_keys, id_rsa, id_ed25519
- ssh_host_rsa_key/.pub und ssh_host_ed25519_key/.pub
- splash.png und www-public einschließlich Unterverzeichnissen

Kernel, DTB, Bootskript und Dateisystemkennungen stammen immer aus dem neuen
Image. Beliebige Änderungen unter /etc, nachinstallierte Pakete und Browserdaten
im Root-Dateisystem werden nicht übernommen. Es wird nur eine private Kopie der
oben genannten Einstellungen angelegt, **kein Backup des gesamten alten Images**.
Diese Kopie bleibt für eine Wiederherstellung nach einem Schreibfehler erhalten.
Die Werkzeuge ersetzen das System; ein Stromausfall während des Schreibens kann
erneutes Flashen erforderlich machen. Noch kein Hardware-Update als erfolgreich
getestet behauptet; die FAT-Übernahme ist mit echten Dateisystemabbildern getestet.

## Vorhandene SD aktualisieren – solo oder kombiniert

Auf einem Linux-PC mit Python 3 und mtools. SD aus der ausgeschalteten Box nehmen.
Alle Partitionen der Zielkarte aushängen. Aus demselben neuen Release das gewünschte
SD-Image, manifest.json und update-anotter-sd.py herunterladen.

Beispiel (Image- und Gerätepfad an das tatsächliche Release/Ziel anpassen):

```sh
sudo python3 update-anotter-sd.py \
  --image T95H-AnotterKiosk-VERSION-arm64-sd.img.gz \
  --manifest manifest.json \
  --device /dev/disk/by-id/DEINE-SD-KARTE \
  --settings-dir "$PWD/anotter-einstellungen-$(date +%Y%m%d-%H%M%S)" \
  --work-dir "$PWD"
```

Für die kombinierte SD stattdessen das `-sd-emmc-installer.img.gz` angeben.
Das Arbeitsverzeichnis muss auf dem PC liegen und mindestens 9 GB freien Platz
haben. Die bisherigen Einstellungen werden automatisch gelesen, privat gesichert,
in das neue Image eingesetzt und dort geprüft. Erst nach der Eingabe `SD UPDATE`
wird die Karte geschrieben und vollständig zurückgelesen. Eingehängte Karten,
fremde Layouts, eMMC-Ziele und falsche Prüfsummen werden abgelehnt.
Ein einfacher dd-/Etcher-Flash ohne dieses Werkzeug erhält Einstellungen nicht.

## Bestehende eMMC aktualisieren

Von der **neuen kombinierten SD** booten. Die zu aktualisierende eMMC darf nicht
als Root laufen oder anderweitig eingehängt sein. Installer-Partition 3 der SD
unter `/mnt/t95h-installer` schreibbar einhängen (MMC-Gerätenummer vorher prüfen).
Dann:

```sh
sudo bash /mnt/t95h-installer/install-emmc.sh --update
```

Der Modus erkennt das bisherige T95H-Anotter-eMMC-Layout, liest dessen FAT nur
lesend und übernimmt **die bisherigen eMMC-Einstellungen**, nicht die Einstellungen
der Rettungs-SD. Eine private `anotter-settings-*.tar` bleibt auf der Installer-SD.
Nach ausdrücklicher Bestätigung mit `EMMC LOESCHEN` werden das neue eMMC-Image,
der passende Bootloader und die gespeicherten Einstellungen installiert und geprüft.
Anschließend herunterfahren, Strom trennen und die SD entfernen.

Ohne `--update` bleibt der bisherige Erstinstallationsweg erhalten: Er übernimmt
Einstellungen **von der SD** und ersetzt den eMMC-Inhalt. Fehlende oder nicht
passende bestehende eMMC-Systeme führen im Update-Modus zum Abbruch; es gibt keinen
stillen Rückfall auf Erstinstallation.
