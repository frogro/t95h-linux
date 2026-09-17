# Boot- und OpenWrt-6-Korrekturen, 2026-09-17

## Geltungsbereich

OpenWrt **Kernel 6**: alle vier Profile, SD, eMMC und kombiniertes
SD/eMMC-Installationsimage. OpenWrt mit Kernel 7 bleibt unverändert.
LibreELEC und AnotterKiosk erhalten denselben PMIC-Familienfix in ihren jeweiligen
SD/eMMC-SPLs; das kombinierte Image wird daraus abgeleitet.

WLAN-Vorgabe für Kernel 6: SSID **OpenWrt**, WPA2-Kennwort
**openwrtopenwrt**. Beim Konfigurationsrestore wird ausschließlich der alte
interne AP `T95H-Test` auf diese Vorgabe migriert. Andere SSIDs bleiben erhalten.
Der Restore-Marker schützt weiterhin sonstige Einstellungen und ist kein Bootstopp.

RNDIS war bereits in Paketgruppe A ausgewählt. Jetzt wird zusätzlich geprüft:
`CONFIG_USB_NET_RNDIS_HOST=m`, vorhandenes rndis_host.ko und Installation in
base-A/base-A-B. Die vorhandenen ASIX/AX88179, RTL8152, CDC-Ether, QMI und MBIM
Pakete bleiben. Der vollständige ABI-gebundene Modulfeed wird weiter gebaut.

## Boot und Updates

Die endlose Schlafschleife nach drei fehlgeschlagenen Ladeversuchen entfällt.
Stattdessen kehrt das Skript mit Fehler zu U-Boot zurück. Drei begrenzte
Rescan-/Ladeversuche bleiben. rootwait, Strom-/Spannungsprüfungen und begrenzte
Hardware-Initialisierung bleiben; ihre Entfernung wäre kein belegter Bootfix.
Keine neuen WLAN-Timingexperimente und keine geänderte RAM-Taktrate.

Native Sysupgrade prüft jetzt alte/neue laufende Firmware und das exakt passende
neue Image. Nach FAT/Rootfs-Update wird nur der 40-KiB-SPL aktualisiert und
zurückgelesen; bei SPL-Schreibfehler wird der vorherige SPL zurückgeschrieben.
MBR, spätere Firmware, vergrößerte Rootpartition und eine dritte Installerpartition
bleiben erhalten. Ein Stromausfall während Firmware-Schreiben ist weiterhin ein
Recovery-Risiko; dies ist kein atomarer Dual-Bank-Updater.

Alte native Releases lehnen den neuen Präfix ab. Einmalig die beiden Dateien
`migrate-upgrade.sh` und `platform-dual-update.sh` aus **demselben** neuen Release
nach Prüfung seiner SHA256SUMS auf die Box kopieren. Zunächst
`sh migrate-upgrade.sh --check`, danach `sh migrate-upgrade.sh --apply` ausführen.
Das ersetzt ausschließlich einen exakt bekannten alten Upgradehandler und sichert
ihn unter /root. Danach normal per LuCI/sysupgrade mit Konfigurationsübernahme
aktualisieren. Keine Force-Option. Für andere Altstände ist eine Prüfung nötig.

Das kombinierte SD-Image ist ein **Installationsimage**, keine Sysupgrade-Eingabe.
Seine SD wird mit dem normalen SD-Sysupgrade aktualisiert; die Installerpartition
behält dabei ihr ursprüngliches eMMC-Image und wird nicht automatisch erneuert.
Zum Installieren von dort p3 einhängen und install-emmc.sh starten. Es löscht eMMC
nach ausdrücklicher Bestätigung und übernimmt die SD-Konfiguration als
sysupgrade.tgz für den ersten eMMC-Start.

## Bestehende LibreELEC-/Anotter-Medien

`tools/boot/update.py` bietet ein gesondertes **Offline-Bootupdate** mit
Prüfsummenprüfung, Sicherung und Rücklesekontrolle. Auf einem Linux-Rechner mit
Python3, mtools und dosfstools arbeiten; alle Zielpartitionen vorher aushängen.
Erst prüfen, dann explizit anwenden, z.B. nach sicherer Gerätezuordnung:

```
sudo python3 tools/boot/update.py /dev/sdc --medium sd
sudo python3 tools/boot/update.py /dev/sdc --medium sd --apply --backup /sicherer/pfad/t95h-boot-backup
```

Für eMMC entsprechend `--medium emmc`; auch dieses Medium muss offline und
ungehängt sein. Keine automatische Live-Anwendung. Das Werkzeug erkennt die
alten/neuen Firmwarebereiche unabhängig von den OS-Partitions-IDs. Es ersetzt
nur SPL und bereinigt das vorhandene Bootskript, dessen OS-Argumente erhalten
bleiben. Rootfs, Einstellungen und Partitionstabelle werden nicht geschrieben.
Ein unbekannter Firmwarestand wird abgewiesen. Kein vollständiger LibreELEC-/
Anotter-OS-Updater: der bislang unvollständige LibreELEC-Updateadapter wird dadurch
nicht als fertig erklärt. Alte Images erneut zu flashen würde den Bootfix ersetzen.

## Noch offen

Der neue eMMC-SPL sowie vollständige neue Images/Installer und deren Upgradepfade
müssen auf Hardware getestet werden. SD-SPL ist aus den erfolgreichen lokalen
Tests übernommen; das garantiert keine Kaltstartzuverlässigkeit für jedes Board.

## Lokale Prüfung

102 Repository-Tests und 22 native Pipeline-/WLAN-Tests bestanden.
Darin enthalten: Bootmigration, Installer, LibreELEC/Anotter und begrenzte
ALSA-Initialisierung mit ungültigen Einstellungen und fehlendem Codec. Portpatch gegen den
festgelegten OpenWrt-Commit angewandt. Offline-Update an einer Image-Datei
inklusive Sicherung/Rücklesen sowie Erhalt von MBR, FIT und Rootdaten geprüft.
Kombinierten Installer mit vorhandenen CI-Images als Testdaten vollständig
gebaut: FAT/ext4, eMMC-Payload und Kompressionsrücklesen bestanden. Das ist
kein neu gebautes Release mit allen Änderungen. Neue Vollbuilds und Hardware-
Updates stehen aus. Auf der laufenden Box wurde dabei nichts geändert.

## Multimedia-Ergänzungen

Alle drei Systeme initialisieren den analogen ALSA-Pfad mit begrenzter Wartezeit
und konfigurierbarer Lautstärke; siehe `multimedia-live-validation.md`. OpenWrt 6
Profil B enthält zusätzlich USB-Audio und den korrigierten GStreamer-Scannerpfad.
LibreELEC/Anotter aktivieren USB-Audio explizit im Kernel. Der Elgato HD60X bleibt
an USB2 hinsichtlich Nutzbild/Audio hardwareseitig unbestätigt.
