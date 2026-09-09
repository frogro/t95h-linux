# Gesicherter Kernel-Quellstand

Das lokale Archiv `linux-7.2.3.tar.xz` und seine SHA256 sind in `source-lock.json` gesperrt. `tested-kernel-source.patch` bildet den abgeglichenen finalen Arbeitsstand ab: 56 geänderte Originaldateien und 75 zusätzliche Quell-/Lizenz-/Dokumentationsdateien. Generierte Objekt-, Modul- und Hilfsdateien werden nicht übernommen.

## Wiederherstellung

1. SHA256 des Kernelarchivs und des Patches gegen `source-lock.json` prüfen.
2. Archiv in ein neues Verzeichnis entpacken.
3. Im entpackten Kernelverzeichnis `patch --batch --forward --fuzz=0 -p1 -i /absoluter/pfad/tested-kernel-source.patch` ausführen.
4. Alle Dateien aus `source-lock.json` gegen ihre SHA256 prüfen.

Diese Schritte wurden lokal in einem frischen Archivbaum ausgeführt. Alle 131 Delta-Dateien und 94.699 unveränderte Originaldateien wurden geprüft. `source-replay-proof.json` dokumentiert das Ergebnis; lokale Pfade darin sind Prüfnachweise, keine Buildvoraussetzungen.

## Abgrenzung

Dies ist eine konsolidierte Sicherung des vorhandenen Quellstands, noch keine fertig freigegebene Basis/A/B-Buildpipeline. Historische Patches nicht zusätzlich darüber anwenden. Die ursprünglichen Änderungen und noch offenen semantischen Prüfungen stehen in `historical-dispositions.json`.

Noch separat zu sperren und zu reproduzieren: finale Kconfig pro Profil, Firmware, externe Regulator-/ANA-Module, tatsächlich ausgelieferter DTB, Bootkette und OS-Dienste. Ein erfolgreicher Quellvergleich ist kein erfolgreicher frischer Kernelbuild und keine Hardwareprüfung. Die gemeinsame SRAM-Unterstützung ist bereits im Archiv enthalten. Ein alter TMDS-Quirk und der verworfene PPU-Einschaltversuch sind nicht im finalen Quellstand enthalten.
