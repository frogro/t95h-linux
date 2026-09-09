# Geplanter Buildvertrag

Eingabe: Board-ID, OS-ID, Version (OpenWrt: stable-latest), freigegebenes Hardwareprofil.
Auflösung: offizielle Releasequelle prüfen, konkrete Version und Quell-Commits/Hashes sperren.
Build: isolierter Arbeitsbaum, benötigte Tools/Quellen per Lock, kein SD-/eMMC-Zugriff.
Ergebnis: Raw-Installationsimage und passende OS-spezifische Updatedatei (OpenWrt: sysupgrade), SHA256SUMS, Buildprotokoll, Manifest, Paketliste, Patchliste und Prüfnachweise.
Validierung: Format/Layout statisch; OS- und Hardwaretests als eigener Freigabestatus.
Installer: startet Auftrag, zeigt Status und verifiziert Download; Flashen nur mit separat eindeutig ausgewähltem Datenträger.

Freigegebene Board-Bootkette und Betriebssystemversion werden separat versioniert. Eine neue Kernelversion erbt keine Hardwarefreigabe automatisch. Der erste Workflow soll dasselbe lokale Buildskript ausführen, keine zweite Implementierung des Buildvorgangs.

Stand 2026-09-09: ein Build pro Auftrag, kein zweiter A/B-Vergleich. Quellprüfung und Stable-Auflösung sind über prepare-openwrt.yml ausführbar. Vollständiger Imagebau steht noch aus.
