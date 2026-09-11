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

## Eigene Zugangsdaten

Passwörter und WLAN-Einstellungen nach der Installation über LuCI oder SSH ändern.
GitHub Actions baut ausschließlich mit den öffentlichen Standards. Persönliche
Passwörter und private SSH-Schlüssel gehören nicht in öffentliche Images.
