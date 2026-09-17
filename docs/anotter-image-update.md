# AnotterKiosk auf T95H: neue Version als Image

Upstream dokumentiert das Herunterladen und Flashen eines Images:
https://github.com/Manawyrm/AnotterKiosk#how-to--installation-guide
Ein freigegebener In-place-/Auto-Updater ist dort nicht vorhanden:
https://github.com/Manawyrm/AnotterKiosk/issues/9
Der Autor warnt vor seinem experimentellen In-place-Skript. Es wird nicht
mitgeliefert; insbesondere kollidiert dessen Hilfspartition mit unserem Installer.
APT aktualisiert Debian-Pakete, ist aber kein vollständiger Anotter/T95H-Image-Updater.

## SD

1. Passendes aktuelles T95H-Anotter-Image aus frogro/t95h-linux herunterladen;
   keine Raspberry-Pi- oder x86-Images verwenden. SHA256SUMS vergleichen.
2. Wer bestehende Einstellungen weiterverwenden möchte, kopiert vorher die
   benötigten Dateien von der FAT-Partition: kioskbrowser.ini, authorized_keys,
   wpa_supplicant.conf, eigene splash.png/www-public und gegebenenfalls private
   SSH-/Tunnel-Schlüssel. Private Dateien ausschließlich lokal aufbewahren.
   Dies ist optional und kein automatisch erzwungenes Vollbackup.
3. Normales SD-Image oder kombiniertes SD/eMMC-Installer-Image entpacken und auf
   die gesamte, ausgehängte SD schreiben. Der vorhandene SD-Inhalt wird ersetzt.
4. FAT erneut öffnen und die gewünschten Konfigurationsdateien eintragen oder
   zurückkopieren. Keine alten Kernel-, DTB- oder Bootskripte zurückkopieren.
5. SD sicher entfernen und die Box booten. Es gibt keinen eigenen Updatekanal
   und keinen zusätzlichen automatischen Updater.

## eMMC und kombinierte SD

Das kombinierte Image startet auf SD und enthält zusätzlich das passende eMMC-
Installationsimage. Es schreibt beim Booten nicht automatisch auf eMMC.
Der enthaltene install-emmc.sh ist eine ausdrücklich bestätigte Neuinstallation,
kein Update bestehender eMMC-Daten. Er übernimmt die Konfiguration der SD,
einschließlich wpa_supplicant.conf, aber ersetzt den bisherigen eMMC-Inhalt.
Bestehende eMMC-Einstellungen bei Bedarf vorher selbst auf die Installer-SD
übertragen. Siehe media-emmc-installation.md im Repository.

Ein späteres Image-Flashen ersetzt die bisherige Installation. Ein Erhalt aller
beliebigen Änderungen im Root-Dateisystem wird nicht zugesagt. Dieser Ablauf
entspricht dem Upstream-Imageverfahren, angepasst an die T95H-Medien und Images.
