# Standardzugang und lokale Erstkonfiguration

Die T95H-Images erhalten bewusst folgende **öffentliche Standardzugangsdaten**:

| Zugang | Standard |
|---|---|
| AP-Name | `openwrt` |
| WLAN-Passwort (WPA2) | `openwrtopenwrt` |
| SSH-/LuCI-Benutzer | `root` |
| Root-Passwort | `openwrt` |
| Webterminal-Zusatzanmeldung | `root` / `openwrt` |
| WLAN-Adresse der Box | `192.168.50.1` |
| Ethernet-Adresse | DHCP vom angeschlossenen Router |

`192.168.178.177` ist die Adresse im bisherigen Testnetz, kein fest eingebauter
Standard. Die Standards ermöglichen die Erstinstallation; anschließend eigene
Passwörter setzen. Sie sind keine privaten Geräteschlüssel. SSH-Hostschlüssel
und TLS-Schlüssel werden pro Installation erzeugt, nicht aus Backups übernommen.

## Installer

```sh
python3 installer/t95h.py access
```

Der Installer fragt unabhängig voneinander:

1. Root-Passwort für SSH/LuCI/Terminal: Enter übernimmt `openwrt`.
2. „Möchten Sie zusätzlich einen WLAN-AP einrichten?“ (Vorgabe: ja).
3. Falls ja: SSID mit Vorgabe `openwrt` und WLAN-Passwort mit Vorgabe
   `openwrtopenwrt`; Enter übernimmt jeweils den Standard.

Bei nein werden der vorbereitete AP und dessen DHCP-Server deaktiviert;
Ethernet mit DHCP bleibt als Zugang erhalten. Eigene Passwörter werden verdeckt
und mit Wiederholung abgefragt. Das Ergebnis ist ein lokales
Erststartskript unter `private/firstboot/99-t95h-local-access` (Dateimodus 0600).
Der Ordner ist von Git ausgeschlossen. Eine vorhandene Auswahl wird nicht
überschrieben. Root- und Webterminal-Passwort werden gemeinsam gesetzt.

**Aktueller Stand:** Die Abfrage und Skripterzeugung sind implementiert. Der
Flash-Installer muss dieses Skript noch nach Prüfung des heruntergeladenen
Images lokal in `/etc/uci-defaults/99-t95h-local-access` auf der Ziel-SD einsetzen.
Das Skript wird vor dem ersten Start eingesetzt, niemals im laufenden System
oder beim normalen Sysupgrade. Es enthält Passwörter im Klartext und bleibt
lokal. Der Installer darf es nicht an GitHub senden oder in Release-Artefakte
aufnehmen. GitHub Actions baut ausschließlich mit öffentlichen Standards.

Bei Sysupgrade werden vorhandene Konfiguration und Root-/SSH-Zugangsdaten
beibehalten. Die Erstkonfiguration darf sie nicht erneut auf Standards setzen.
Die eigenständige Rootfs-Erzeugung muss den Standard-Rootzugang noch explizit
initialisieren und prüfen; das reine Kopieren der WLAN-Konfiguration reicht
hierfür nicht aus.
