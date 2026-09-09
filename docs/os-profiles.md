# OS-Profile und gemeinsame Hardwarebasis

Stand 2026-09-07: Architekturvorgabe; andere Distributionen noch nicht gebaut oder hardwaregeprüft.

## Gemeinsamer Board-Unterbau

Die getestete Bootkette, Linux-7.2.3-Patchbasis, Device-Tree-Vorlagen, Firmware und Hardware-Abhängigkeiten werden unabhängig von OpenWrt verwaltet. Kernelmodule müssen stets zum tatsächlich gebauten Kernel einschließlich Konfiguration und ABI passen. Für andere Distributionen können zusätzliche Kerneloptionen erforderlich sein; identische Kernel-Binärdateien sind daher keine Voraussetzung und nicht garantiert.

- Basis: Boot/SD/USB-Grundfunktionen, Ethernet, internes WLAN/AP, CPU/Thermal, Frontdisplay, HDMI-Konsole und Analog-/HDMI-Audio. Gemeinsam benötigte SRAM-, IOMMU-, Regulator- und Taktfunktionen bleiben hier.
- A: zusätzliche USB-Netzwerkgeräte und Modems, soweit nicht bereits Bestandteil der anwendbaren OS-Basis.
- B: Panfrost/Mesa, Cedrus-Decoding, USB-UVC-Videoaufnahme sowie benötigte Aufnahme-/Streaming-Bibliotheken und Werkzeuge. Weitere Grabber-Chipsätze werden anhand unterstützter Geräte-IDs aufgenommen. B hängt von Basis ab, nicht von A. Hardware-Encoding ist nicht zugesagt.

Alle vier Kombinationen Basis, Basis+A, Basis+B und Basis+A+B müssen für jedes freigegebene OS aufgelöst und geprüft werden. Insbesondere muss Basis+B ohne Modem- oder zusätzliche USB-WLAN-Pakete funktionieren.

## Distributionsadapter

| Adapter | OS-spezifische Aufgaben | Stand |
|---|---|---|
| OpenWrt | Target-Standardpakete, APK, LuCI, UCI/procd, WLAN/AP, sysupgrade und Konfigurationsübernahme | Lokaler vollständiger Kandidat getestet; Profilaufteilung noch in Arbeit |
| Allgemeines Linux / DietPi | Passendes Rootfs, Paketverwaltung, Init-Dienste, Netzwerk/AP, Berechtigungen und Updateverfahren | Geplant |
| Linux mit Kodi / LibreELEC | Zusätzlich Mesa/EGL/DRM und zum Cedrus-Request-Treiber passende Decoder-Anbindung, Audio, IR und Medienoberfläche | Geplant, Kompatibilität je OS zu prüfen |

LuCI, APK, UCI und procd gehören ausschließlich in den OpenWrt-Adapter. Gemeinsame Hardware-Dienste (Display, späte WLAN-Initialisierung, GPU-Provider) brauchen entsprechende Dienstdefinitionen für das jeweilige Init-System. Ein vorhandenes Video-Gerät allein belegt keine funktionierende Hardware-Decodierung in Kodi.

## Auswahl und Updates

Der Installer speichert OS, Board, Basis/A/B, zusätzlich gewählte Pakete und vollständig aufgelöste Abhängigkeiten im Release-Manifest. Jede daraus erzeugte Updatedatei enthält dieselbe Auswahl wie ihr Installationsimage. Beim nächsten Release wird diese Auswahl erneut gegen das neue OS aufgelöst; entfallene oder inkompatible Pakete führen zu einem erklärten Abbruch statt stiller Entfernung.

OpenWrt-Kernelmodule werden aus unserer gesperrten Kernelbasis gebaut und als passende eigene Pakete bereitgestellt. Ein späterer Paketfeed darf nur zur Kernel-ABI passende Module anbieten. Die Auswahl muss sowohl bei Image-Updates als auch beim Angebot einzelner Modulupdates beachtet werden. Ein neuer Kernel erfordert den zusammengehörigen Kernel-/DTB-/Modulsatz; ein beliebiger offizieller OpenWrt-kmod ist kein Ersatz.

Für andere Distributionen ist ein eigener Updateadapter erforderlich. Eine OpenWrt-sysupgrade-Datei ist kein distributionsübergreifendes Update. Konfiguration, Geräteidentität und wiederherstellbare Auswahl müssen je Adapter geprüft werden. Persönliche Schlüssel dürfen nicht in öffentliche Images gelangen.

## Freigabeprüfung

Quell- und Abhängigkeitsprüfung, sauberer Build und Artefaktprüfung erfolgen pro OS und Profil. Boot, Basisfunktionen und tatsächliche Multimedia-Nutzung werden auf der Box separat validiert. Erfolgreiche OpenWrt-Tests übertragen keine automatische Hardwarefreigabe auf ein anderes OS.

## Reihenfolge bestätigt 2026-09-07

Die konkrete Umsetzung und Prüfung anderer Betriebssysteme wird auf ein späteres, gemeinsam ausgewähltes Beispiel verschoben, voraussichtlich Debian- oder Ubuntu-basiert. Aktuell werden ausschließlich OpenWrt-Profile, Build und Updateintegration umgesetzt. Die Trennung zwischen Hardwareunterbau und OS-Adapter bleibt Architekturvorgabe; ein zweiter OS-Adapter ist keine Voraussetzung für den Abschluss der jetzigen OpenWrt-Arbeit. Es wird noch keine konkrete Distribution oder Version festgelegt.
