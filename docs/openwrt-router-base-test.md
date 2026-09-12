# Router-Basis: erster Testbuild nach dem Modulabgleich

Diese Erweiterung gilt für base, base-A, base-B und base-A-B. Sie schließt die
erste Gruppe klarer Router-Lücken, nicht den gesamten 976-Pakete-Katalog.

Enthaltene Gruppen:
- CryptoAPI/AF_ALG, HMAC, CMAC, SHA2/SHA3 und RNG einschließlich Abhängigkeiten.
- WireGuard, UDP-Tunnel, TUN und VETH.
- nftables Socket/TPROXY und Bridge-Erweiterungen.
- Traffic-Shaping: Scheduler/Klassifizierer, CAKE und IFB.

Die exakten 26 Paketzuordnungen stehen in
`boards/t95h/kernel/base-module-contract.json`. Alle bislang eingeschalteten
Kerneloptionen behalten ihren y/m-Modus. TUN wird eingebaut, um das bisher
fest eingebaute VHOST_NET nicht durch seine TUN-Abhängigkeit auf ein Modul
herabzustufen. Andere neue Treiber sind überwiegend Module. Keine Änderungen
an Bootloader, DTB, WLAN-Treiber oder GPU-Startparametern.

## Was APK damit kann

Der bestehende signierte `t95h-kernel` enthält die passenden Funktionen und
Module und meldet die geprüften `kmod-*`-Namen als virtuelle Provider. Anwendungen
mit diesen Abhängigkeiten können sie deshalb als erfüllt erkennen. Die
zusätzlichen Funktionen müssen dafür bereits mit diesem Image installiert sein.

Das ist **kein separater kmod-Downloadfeed**: Nachladen weiterer, bislang nicht
gebauter Treiber bleibt offen. Offizielle Kernelmodule passen weiterhin nicht
zu unserem Kernel. Die Umsetzung eines signierten, separat versionierten Feeds
wird nicht durch virtuelle Provider ersetzt.

Der Build verlangt für jeden neuen Provider alle benötigten Kerneloptionen und
die zugeordneten tatsächlichen `.ko`-Dateien oder `modules.builtin`-Einträge.
Die vorhandene Buildkette prüft Modul-Vermagic, Hashes, flache Modulabhängigkeiten
und die APK-Signatur. Der echte APK-Solver muss alle 26 kmod-Namen zusammen mit
dem eigenen Kernelpaket installieren können, ohne offizielle Kernelpakete.
`base-module-verification.json` und der vollständige Vertrag liegen im Release.

## Validierung und Hardwaretest

Lokal wurden alle vier Konfigurationen mit dem exakten Linux-7.2.3-Quellstand und
dem OpenWrt-AArch64-Compiler durch `olddefconfig` aufgelöst. Kein vorher aktives
y/m-Symbol ging verloren. 75 Tests, Repository-Prüfung und Diffprüfung bestanden.
Die eigentliche Kompilierung, Modulprüfung und Paketauflösung erfolgen in Actions;
diese Ergebnisse sind vor Build-Abschluss noch nicht bestätigt.

Zuerst das neue Image von SD starten. Prüfen: Boot/SSH/Ethernet, WPA2-Verbindung,
Anwendungsinstallation (z. B. wireguard-tools), Laden von WireGuard/VETH/CAKE/IFB,
WireGuard-Verbindung und Traffic-Shaping. Erst nach diesen Laufzeittests das
eMMC-System aktualisieren. Keine dieser Funktionen wurde während der
Vorbereitung auf der laufenden Box verändert.
