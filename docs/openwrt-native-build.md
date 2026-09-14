# OpenWrt mit Kernel 6 bauen

Der separate Workflow `build-openwrt-native.yml` baut die T95H-Portierung gegen die bei jedem Start aktuell als stabil ausgewiesene OpenWrt-Version. Tag und Commit werden einmal ermittelt und für den gesamten Lauf festgehalten. Ein Wechsel auf einen anderen Kernel-Hauptzweig oder nicht mehr passende Patches bricht den Lauf zur Prüfung ab.

## Lokal starten

Voraussetzung: GitHub CLI (`gh`), Anmeldung mit `gh auth login` und Schreibberechtigung für das Repository.

```bash
gh workflow run build-openwrt-native.yml --repo frogro/t95h-linux --ref main -f profile=base
```

`profile=` wählt genau eine Variante:

| Profil | Inhalt |
|---|---|
| `base` | T95H-Hardware, LuCI, internes WLAN/AP-Unterstützung, Kryptografie, WireGuard, TUN/VETH, nftables-Erweiterungen und CAKE/IFB |
| `base-A` | Zusätzlich USB-Netzwerk-, WLAN- und Mobilfunkadapter sowie zugehörige Einrichtungsprogramme |
| `base-B` | Zusätzlich Multimedia-Anwendungen, GStreamer, UVC-Webcams und Streaming-Werkzeuge |
| `base-A-B` | Beide Erweiterungen |

Der AP ist bei einer frischen Installation nicht automatisch aktiviert. WLAN in LuCI konfigurieren. Beim Update mit beibehaltenen Einstellungen bleibt die WLAN-Konfiguration erhalten. GPU/CPU-Unterstützung, HDMI, Audio und IR gehören zu allen Profilen; B ergänzt Anwendungen.

```bash
gh run list --repo frogro/t95h-linux --workflow build-openwrt-native.yml --limit 5
gh run watch RUN_ID --repo frogro/t95h-linux
```

## Ergebnisse und Updates

Bei Erfolg veröffentlicht der Workflow ein Testrelease mit SD- und eMMC-Installationsimages, jeweils einer passend benannten Sysupgrade-Datei, Prüfsummen, Paketliste und Build-Protokoll. Installations- und Update-Datei desselben Mediums sind inhaltsgleich. Für LuCI das Update-Image des laufenden Mediums wählen und „Einstellungen behalten“ aktivieren. Das gilt auch beim Profilwechsel. Nachinstallierte Pakete werden nicht automatisch erneut installiert.

Der signierte Kernelmodulfeed wird vor den Images als separates GitHub-Release veröffentlicht und ist bereits im Image eingetragen. Enthalten sind alle für das Ziel durch OpenWrt auswählbaren Kernelpakete, nicht architekturfremde oder widersprüchliche Pakete. Signierschlüssel: vorhandenes Actions-Secret `T95H_APK_SIGNING_KEY`; private Schlüssel werden weder veröffentlicht noch im Build-Cache gespeichert.

Der Cache wird nur bei identischer Stable-Revision, Portdateien, Konfiguration, Signierschlüssel und Profil wiederverwendet. Ein fehlender oder verworfener GitHub-Cache führt zum Neubau. Feed-Identität enthält zusätzlich zur Kernel-ABI einen Fingerprint; vorhandene veröffentlichte Feeds dürfen nicht verändert werden. Jeder Lauf prüft Paketvollständigkeit, ABI und beide Imagepfade erneut. Ein Cache ist keine dauerhafte Archivgarantie.

Der Workflow kompiliert auf GitHub, nicht auf dem ThinkPad. Persönliche Flash-/Installationshelfer bleiben lokal. Das eMMC-Installationsimage ist kein aus dem laufenden eMMC-System ausführbarer Installer.
