# eMMC-Auslesen aus OpenWrt auf SD

Diese Diagnosewerkzeuge gehören nicht automatisch in ein Release-Image.
Der reguläre Board-DTB lässt die interne eMMC deaktiviert.

Für den aktuellen isolierten Hardwaretest wurde ausschließlich der eMMC-Knoten
im laufenden SD-DTB abgeleitet: aktiviert, 8 Bit, maximal 25 MHz, keine schnellen
DDR-/HS-Modi, keine SD-/SDIO-Suche. Die vorhandene Versorgung wird übernommen;
keine PMIC-Spannung wird geändert. Das ist noch kein validiertes Boardprofil.

`block-readonly.c` setzt ausschließlich Linux-BLKROSET auf 1, prüft danach
BLKROGET und akzeptiert nur Blockgeräte eines durch sysfs identifizierten
MMC-Geräts. Die laufende SD wird abgelehnt. `readonly-start.sh` wird im Test früh
und bei Block-Hotplug ausgeführt. Das ist Software-Schreibschutz, kein physischer
Forensik-Schreibblocker und keine dauerhafte eMMC-Schreibschutzprogrammierung.
Kein Befehl setzt den Schreibschutz zurück oder schreibt Datenblöcke.

Nach dem Teststart:

```sh
python3 tools/emmc/read-boot-areas.py --output /projekt/private/emmc-boot-backup
```

Voraussetzungen: Python-paramiko, bekannter verifizierter SSH-Hostschlüssel,
erkannte und schreibgeschützte eMMC-Bootbereiche. Alle Bereiche werden vorab
identifiziert, anschließend zweimal gelesen und mit der gespeicherten Datei
verglichen. Der Zielordner muss neu sein. Keine automatische Übertragung nach
GitHub. Bootinhalte können gerätespezifische Informationen enthalten.
RPMB wird damit nicht ausgelesen; das ist kein gewöhnliches Blockgerät.
