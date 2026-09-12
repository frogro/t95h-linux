# OpenWrt-Modulkatalog: Abgleich und Katalog-Build

Stand: 12. September 2026. Der neue Actions-Schalter `module_catalog` baut ein
separates A+B-Image mit einem erweiterten, signierten Modulfeed. Der vorhandene
Zwei-Pakete-Test bleibt separat anwählbar. Normale Builds ändern sich nicht.

## Was vollständig ist – und was noch fehlt

**Alle 976 veröffentlichten Kernelpakete** von OpenWrt 25.12.5,
sunxi/cortexa53, wurden erfasst. Das bedeutet ausdrücklich **nicht**, dass alle
976 Pakete bereits für unseren Linux-7.2.3-Kernel verfügbar sind.

Die Eingangsbewertung enthält 730 Konfigurationskandidaten, 129 Pakete aus
externen Treiberquellen, 49 noch offene Zuordnungen zwischen Kernelversionen
und 68 Abhängigkeits-/Profilbeschränkungen. Beispiele für externe Quellen sind
OpenWrts WLAN-Backports, xtables-addons und weitere separat gepflegte Treiber.
Einige entsprechende Funktionen sind schon in unseren Profilen vorhanden;
das beweist noch keine gleichwertige individuelle Paketierung des gesamten
Upstream-Pakets.

Die endgültige Zahl nachladbarer Pakete entsteht **erst nach dem Kompilieren**:
fehlende Moduldateien oder nicht verfügbare Paketabhängigkeiten schließen das
betroffene Paket und dessen abhängige Pakete aus. Diese Ausschlüsse bleiben
in `catalog-audit.json` im Release sichtbar. Ein vollständiges Angebot aller
Upstream-Pakete bleibt damit weitere Portierungsarbeit, kein zugesicherter
Zustand dieses Testbuilds.

## Nachweise und Versionsanpassungen

Referenz: OpenWrt-Commit
`f5dae5ece4805730c5e2850f8aa84765af2f6b32`, signierter Index für
`6.12.94-1-54c42a9af64da421c37305c250430d94`. Alle 976 Original-APKs wurden
über APK gegen den signierten Index bezogen. Daraus stammen Dateilisten,
Paketabhängigkeiten und die in `boards/t95h/kernel/module-catalog.json`
festgehaltenen SHA256-Werte. Fremde Binärmodule werden niemals installiert
oder in das neue Image kopiert.

Für Linux 7.2 sind unter anderem SHA1/SHA256/SHA512-Bibliotheken mit ihrer
ARM64-Beschleunigung, CRC32C, GF128MUL sowie nftables-Kern/Logging/Flow-Offload
anhand der tatsächlichen Kernel-Kconfig-/Makefiles neu zugeordnet. Jede
explizite Anpassung steht beim Paket als `kernel_version_mapping`.
Upstream-`=n`-Einträge sind schwache Rezeptvorgaben: Andere ausgewählte Pakete
dürfen zusätzliche Funktionen aktivieren. Sie werden nicht als generelles
Verbot einer kompatiblen Paketkombination behandelt.

Die erweiterte A+B-Konfiguration wurde mit dem originalen Linux-7.2.3-
`olddefconfig` und unserem OpenWrt-Crosscompiler aufgelöst. Kein bereits
aktiviertes `y`/`m` der bisherigen A+B-Konfiguration wurde verändert oder
entfernt. Die Voranalyse nutzte Kconfiglib mit rein lesender Normalisierung
der neueren Kconfig-Syntax; maßgeblich ist die abschließende Prüfung mit dem
originalen Kernelwerkzeug. Zusätzlich kommen 777 Moduloptionen hinzu.
DTB, Bootloader und gesperrte Treiberquellen werden durch diese Arbeit nicht
geändert. Ein größerer Kernel braucht dennoch einen erneuten Hardwaretest.

## Paketierung und Installation

- Bisherige Boot-/Profilmodule und ihre Abhängigkeiten bleiben im Kernelpaket.
- Jede zusätzliche Moduldatei hat genau einen Paketbesitzer.
- Gemeinsam genutzte Dateien und ELF-Modulabhängigkeiten erzeugen passende
  Paketabhängigkeiten. Bereits eingebaute Funktionen benötigen keine Kopie.
- Metapakete ohne eigene Dateien können eingebaute Funktionen oder andere
  passende Pakete voraussetzen; sie werden im Bericht entsprechend bezeichnet.
- Alle Pakete verlangen die genaue `t95h-kernel`-Version **und** Kernel-ABI.
- APK-Index und Pakete werden signiert; URL und öffentlicher Schlüssel liegen
  bereits im Image. Zum Nachladen: `apk update`, dann `apk add PAKETNAME`.
- Das automatische Laden und die Hardwarefunktion jedes einzelnen Treibers
  sind nicht durch den Build bewiesen. Bei Bedarf zunächst `modprobe MODUL`.

Vor Veröffentlichung prüft der Build mit dem echten APK-Werkzeug über einen
lokalen HTTP-Server die Installation/Entfernung des gesamten erzeugten Feeds,
den Erhalt des Kernel-Images sowie die Ablehnung einer falschen Kernel-ABI
und eines nicht vertrauenswürdigen Index. Das ergänzt die Image-/Upgrade-
Prüfungen. Es ersetzt keinen Hardware- oder Langzeittest.

## Lokale Prüfungen

85 Unit-Tests, Repository-Prüfung, originaler Kconfig-Abgleich und echte
APK-Integrationstests für Zwei-Pakete- und Katalogmodus bestanden. Der
Katalog-Integrationstest verwendet absichtlich nicht ladbare Testdateien und
prüft Paketabhängigkeiten einschließlich gemeinsam genutzter Dateien und
leerer Metapakete. Actions wiederholt die Paketmanager-Prüfung mit den real
kompilierten ARM64-Modulen.
