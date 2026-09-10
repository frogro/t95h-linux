# Gesamten Speicher von SD und eMMC nutzen

Stand: Release `t95h-34413173108-1`. Die Anleitung beschreibt auch manuelle,
noch nicht auf der Box geprüfte Änderungen. Es gibt noch keinen automatischen
Befehl zur Erweiterung des Speichers.

## Was das aktuelle Image verwendet

| Medium | Partition 1 | Partition 2 | Partition 3 | Rest |
| --- | --- | --- | --- | --- |
| Normale SD / installiertes eMMC | 64 MiB FAT, `/boot` | 1932 MiB ext4, `/` | fehlt | nicht zugeordnet |
| SD mit eMMC-Installer | 64 MiB FAT, `/boot` | 1932 MiB ext4, `/` | 256 MiB Installer-Paket | nicht zugeordnet |

Vor Partition 1 liegen 4 MiB mit Partitionstabelle und Bootkette. Diese dürfen
nicht formatiert, verschoben oder durch eine neue Partitionstabelle ersetzt
werden. Der eMMC-Installer löscht derzeit auch den ungenutzten eMMC-Rest;
er richtet dort keine Datenpartition ein. Eine erneute eMMC-Installation löscht
auch eine später eingerichtete Datenpartition.

Eine nominelle 8-GB-eMMC der Testbox meldet 7.818.182.656 Byte (7,28 GiB).
`df -h` zeigt die Größe der eingebundenen Dateisysteme, nicht die gesamte
Kapazität des Mediums. Mehr nutzbarer Speicher entsteht erst durch Partitionierung,
Formatierung bzw. Dateisystemvergrößerung und Einbindung.

## Aktuelle Grenze: Sysupgrade

**Wer die derzeitige Sysupgrade-Funktion weiter benutzen will, darf die
Partitionstabelle des Systemmediums vorerst nicht verändern.**

`boards/t95h/openwrt/upgrade/platform.sh`, Funktion `t95h_target_check`, prüft
Start und Größe von Partition 1 und 2 sowie den SHA256 des gesamten
4-MiB-Bootbereichs einschließlich MBR. Auch das bloße Hinzufügen einer
Datenpartition verändert diesen Hash. Das aktuelle Sysupgrade lehnt das
geänderte Layout dann ab. Die Prüfung nicht mit `-F` oder einem geänderten
Erwartungswert umgehen.

Eine Rootfs-Vergrößerung wäre außerdem nicht dauerhaft: Das Upgrade schreibt
wieder ein Dateisystem mit 1932 MiB. Eine zusätzliche Datenpartition ist daher
für Nutzdaten der sinnvollere zukünftige Weg; sie vergrößert aber **nicht** den
Platz für regulär nach `/` installierte APK-Pakete.

Bis die Upgrade-Prüfung dafür angepasst und getestet ist, kann ein separates
USB-Speichermedium für Daten verwendet werden, ohne die Partitionstabelle des
Systemmediums zu ändern. Kernelmodule müssen dabei aus unserem passenden
T95H-Build stammen, nicht aus einem fremden OpenWrt-Kernelpaket.

## Medium unter OpenWrt eindeutig bestimmen

Als root, zunächst nur lesend:

```sh
cat /proc/partitions
cat /proc/cmdline
cat /proc/mounts
for d in /sys/block/mmcblk[0-9]; do
    echo "$d"
    cat "$d/device/type" "$d/device/cid"
    cat "$d/size"
done
```

`SD` kennzeichnet die Karte, `MMC` die eMMC. `size` ist die Anzahl der
512-Byte-Sektoren. Gerätenummern können sich ändern: nicht ungeprüft
`mmcblk0` oder `mmcblk2` übernehmen. Die aktive Rootpartition lässt sich über
`/proc/self/mountinfo` und den dortigen Major:Minor-Wert unter
`/sys/dev/block/` zuordnen; `/dev/root` allein reicht dafür nicht.

## Manuelle Nutzung des Restbereichs als Datenpartition

**Experimentell, derzeit nicht mit unserem Sysupgrade kompatibel.** Vorher
Daten und Partitionstabelle extern sichern. Die folgenden Schritte setzen
voraus, dass das Zielmedium nicht als laufendes System benutzt wird:
SD am ThinkPad bearbeiten; eMMC von einer separaten Rettungs-SD aus bearbeiten.
Auch `/boot` und andere Partitionen des Zielmediums dürfen nicht eingehängt sein.

1. Mit `fdisk -l /dev/GERAET` die vorhandenen Partitionen und freien Sektoren
   prüfen. `GERAET` steht für das zuvor identifizierte vollständige Medium.
2. Mit `fdisk /dev/GERAET` nur eine neue primäre Linux-Partition im freien
   Bereich anlegen (`n`, anschließend mit `p` kontrollieren, erst dann `w`).
   Keine neue DOS-/GPT-Tabelle erzeugen; keine vorhandene Partition löschen.
   Bei normaler SD/eMMC ist dies Partition 3 ab Sektor **4096000**.
   Bei der Installer-SD bleibt Partition 3 erhalten; Daten werden Partition 4
   ab Sektor **4620288**. Das Ende kann der letzte verfügbare Sektor sein.
   Diese Werte gelten ausschließlich für das oben genannte Release-Layout
   mit 512-Byte-Sektoren; vor dem Schreiben mit der tatsächlichen Tabelle abgleichen.
3. Kann der Kernel die Tabelle wegen eines belegten Geräts nicht neu einlesen,
   nicht mit alten Gerätenodes weiterarbeiten. Geordnet neu starten und die
   Zuordnung, den Start und die Größe der neuen Partition erneut kontrollieren.
4. **Nur die neue, leere Datenpartition** mit ext4 formatieren. Dafür wird
   `mkfs.ext4` aus `e2fsprogs` benötigt. Auf OpenWrt 25.x können fehlende
   Userspace-Werkzeuge mit `apk update` und `apk add fdisk e2fsprogs block-mount`
   installiert werden, sofern sie im konfigurierten Release-Feed verfügbar sind.

   ```sh
   # Platzhalter ersetzen, niemals auf das gesamte Medium anwenden:
   mkfs.ext4 -L T95HDATA /dev/NEUE_DATENPARTITION
   block info /dev/NEUE_DATENPARTITION
   ```

5. Die ausgegebene Dateisystem-UUID für die Einbindung unter `/mnt/data` verwenden.
   Erst prüfen, dass der UCI-Abschnitt `fstab.t95h_data` noch nicht anderweitig
   verwendet wird; vorhandene Fstab-Einstellungen, insbesondere `/boot`, erhalten.

   ```sh
   mkdir -p /mnt/data
   uci set fstab.t95h_data='mount'
   uci set fstab.t95h_data.uuid='UUID_DER_NEUEN_DATENPARTITION'
   uci set fstab.t95h_data.target='/mnt/data'
   uci set fstab.t95h_data.fstype='ext4'
   uci set fstab.t95h_data.options='rw,noatime'
   uci set fstab.t95h_data.enabled='1'
   uci commit fstab
   block mount
   df -h /mnt/data
   ```

   In `/proc/mounts` kontrollieren, dass `/mnt/data` tatsächlich ein eigenes
   Dateisystem ist. Andernfalls würden dort geschriebene Dateien weiterhin
   die kleine Rootpartition füllen. Nutzdaten von Anwendungen gezielt dort
   ablegen. Dies ist kein Extroot und verschiebt das Betriebssystem nicht.

## Noch umzusetzen für eine updatefähige Lösung

- Zusätzliche Datenpartition automatisch aus freiem Platz erzeugen; die
  Installer-Partition dabei erhalten.
- Upgrade-Prüfung auf unveränderte Bootcode-Bereiche und streng validierte,
  nicht überlappende Partitionen umstellen, statt den veränderlichen MBR
  zusammen mit dem gesamten Bootprefix zu hashen.
- Datenpartition beim SD-/eMMC-Sysupgrade unangetastet lassen; UUID und
  Einbindung erhalten.
- Installation, Update und Neustart mit belegter Datenpartition testen.
- Eine getrennte Option für ein größeres Systemdateisystem prüfen, falls
  zusätzlicher Platz für APK-Pakete benötigt wird.

Diese Punkte sind geplant, im genannten Release noch nicht implementiert.

## OpenWrt-Dokumentation

- [Dateisysteme und UUID-Mounts konfigurieren](https://openwrt.org/docs/guide-user/storage/fstab)
- [Speichermedien formatieren und einbinden](https://openwrt.org/docs/guide-user/storage/usb-drives)

Die allgemeinen OpenWrt-Schritte ersetzen nicht die oben beschriebenen
T95H-spezifischen Layout- und Sysupgrade-Grenzen.
