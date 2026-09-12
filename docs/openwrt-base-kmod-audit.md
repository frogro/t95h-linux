# OpenWrt-Basis: Abgleich der nachrüstbaren Kernelpakete

Stand: 12. September 2026. Der Abgleich bestätigt eine Lücke gegenüber dem Ziel,
OpenWrt-Funktionen über den Paketmanager nachrüstbar zu halten. Funktionierendes
WPA2-WLAN ist kein Nachweis für die Vollständigkeit des Kernelangebots.

## Umfang und Ergebnis

Referenz ist das tatsächlich veröffentlichte Kernelpaketverzeichnis von
OpenWrt **25.12.5**, Target **sunxi/cortexa53**, Kernel
`6.12.94-1-54c42a9af64da421c37305c250430d94`.
Es enthält **976 kmod-Pakete**. Die Paketmetadaten stammen aus dem zugehörigen
ImageBuilder (`f5dae5ece4805730c5e2850f8aa84765af2f6b32`). Verglichen werden die
vier angeforderten T95H-Kernelkonfigurationen und unsere Paketzuordnung.

| Statischer Befund | Basis | Basis+A | Basis+B | Basis+A+B |
|---|---:|---:|---:|---:|
| Abgefragte Optionen aktiv und Paketzuordnung vorhanden | 22 | 33 | 23 | 34 |
| Abgefragte Optionen aktiv, Paketzuordnung fehlt | 76 | 79 | 77 | 80 |
| Fehlende Funktionen bei vollständig zuordenbaren Optionen | 298 | 332 | 300 | 334 |
| Konflikt mit explizit deaktivierter Upstream-Option | 1 | 1 | 1 | 1 |
| Manuell zu prüfen: fehlende Symbolnamen, Ausdrücke oder keine Optionen | 579 | 531 | 575 | 527 |

Das sind **keine Zahlen funktionierender oder defekter Treiber**. Die Metadaten
enthalten auch architekturspezifische Varianten. Linux 7.2 hat gegenüber 6.12
Optionen umbenannt/entfernt; andere Optionen fehlen in einer `.config`, weil ihre
Abhängigkeiten abgeschaltet sind. Auch auf sunxi veröffentlichte PCI-Treiber
sind nicht automatisch sinnvoll auf der T95H. Die bisherigen A/B-Grenzen und
bewusst ausgeschalteten PCI/NVMe/MHI-Funktionen werden nicht aufgehoben.

## Konkrete Lücken

- `crypto-user`: CryptoAPI-Schnittstellen sind ausgeschaltet; keine Paketzuordnung.
- `crypto-hmac` und `crypto-cmac`: Funktionen ausgeschaltet, keine Paketzuordnung.
- `crypto-aead`, `crypto-manager`, `crypto-cbc`, `crypto-gcm`: abgefragte Funktionen
  bereits aktiv, aber keine entsprechende virtuelle Paketzuordnung.
- `wireguard`, `tun`, `veth`: entsprechende Basis-Kerneloptionen ausgeschaltet.
- `br-netfilter`, `nft-socket`, `nft-tproxy`: ebenfalls ausgeschaltet.
- SQM/Traffic-Shaping: mehrere Scheduler und Klassifizierer fehlen; die gesamte
  Abhängigkeitskette einschließlich IFB muss separat aufgelöst werden.
- Beispielsweise ext4, USB-Storage und USB-Audio: Optionen aktiv, Zuordnung fehlt.

Acht bereits beworbene Basis-Provider benötigen zusätzlich einen detaillierten
Abgleich: `crypto-md5`, `lib-crc32c`, `nf-conntrack-netlink`, `nf-conntrack6`,
`nf-flow`, `nf-log`, `nft-core`, `sound-core`. Das beweist noch keine falschen
Paketzusagen: unter anderem sind Kernel-Symboländerungen bereits bekannt.
Die derzeitige Prüfung nur eines Symbols je Provider beweist jedoch nicht die
vollständige Erfüllung aller Funktionen eines offiziellen Kernelpakets.

## Paketierung und noch notwendige Umsetzung

`package-profile-kernel.py` verpackt aktuell sämtliche gebauten Module gemeinsam
mit Image, DTB und Firmware in `t95h-kernel`. Eine kleine feste Tabelle erzeugt
virtuelle `kmod-*`-Provider. Damit existiert **kein vollständiger Feed individuell
nachinstallierbarer Kernelmodule**. Offizielle 6.12-Kernelpakete passen nicht zu
unserem 7.2.3-Kernel und dürfen nicht durch erzwungene Installation verwendet werden.

Nächste Umsetzungsschritte:

1. Architekturunabhängige Router-Funktionen zuerst abdecken: Kryptografie,
   WireGuard/TUN, Firewall-Erweiterungen und Traffic-Shaping. Abhängigkeiten mit
   dem echten Linux-7.2-Kconfig auflösen und in allen Basisvarianten nachweisen.
2. Zu jedem Paket eine vollständige Liste erforderlicher Funktionen und Dateien
   festlegen, inklusive Abweichungen von OpenWrt 6.12. Vorhandene einzelne
   Provider-Symbole genügen dafür nicht.
3. Tatsächliche `.ko`-Dateien bzw. eingebaute Funktionen, Modulabhängigkeiten,
   Firmware und Autoload prüfen. Danach korrekte Paket-Provider erzeugen.
4. Für echte Nachinstallation separat signierte APKs/Index an die **exakte eigene
   Kernel-ABI** binden und einen Paketmanager-Test durchführen. Eine zusätzliche
   Paketzuordnung allein erzeugt noch keinen vollständigen Modulfeed.

Dieser Auftrag führte den **statischen Katalogabgleich** durch. Er aktiviert
noch keine Kerneloptionen, korrigiert noch keine Provider und erzeugt kein neues
Image. Die manuelle Auflösung und Paketierungsumsetzung sind ausdrücklich offen.
Die laufende Box wurde hierfür nicht geändert oder neu gestartet.

## Nachweise und Wiederholung

Vollständiges maschinenlesbares Ergebnis:
[audits/openwrt-kmods-25.12.5.json](audits/openwrt-kmods-25.12.5.json).
Es enthält für jedes Paket den Status in allen vier Profilen, fehlende/abwesende
Symbole, Upstream-Abhängigkeiten sowie SHA256 der Eingaben.

Werkzeug: `tools/audit-openwrt-kmods.py`, mit expliziten Eingaben
`--packageinfo`, `--index-dump` (Ausgabe von `apk adbdump packages.adb`),
`--index-url`, `--upstream-commit` und `--output`.
Der Bericht wertet keine Make-Ausdrücke aus und behauptet keine Laufzeitprüfung.

Quellen:
- [Offizieller Paketindex](https://downloads.openwrt.org/releases/25.12.5/targets/sunxi/cortexa53/kmods/6.12.94-1-54c42a9af64da421c37305c250430d94/)
- [Passender OpenWrt-Quellstand](https://github.com/openwrt/openwrt/tree/f5dae5ece4805730c5e2850f8aa84765af2f6b32/package/kernel/linux/modules)

Validierung: 70 lokale Tests bestanden, darunter sechs gezielte Tests für den
Abgleich; Repository-Prüfung und `git diff --check` erfolgreich.
