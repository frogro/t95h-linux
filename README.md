# T95H Linux / OpenWrt

Privates experimentelles Build-Projekt für die T95H mit H616. Linux 7.2.3,
Board-Patches und die getestete Bootkette bleiben festgelegt. Jeder neue Auftrag
ermittelt die aktuelle stabile OpenWrt-Version einmal und baut genau ein Profil.
Kein A/B-Vergleichsbuild und keine automatischen Hardwaretests.

## Vollständiger Build vom ThinkPad

Im Repository ausführen:

```sh
python3 installer/t95h.py dispatch --profile base-A-B --console dual
python3 installer/t95h.py status
python3 installer/t95h.py download --run-id RUN_ID --profile base-A-B --console dual
```

`dispatch` startet **Build T95H install image and sysupgrade**. Der Workflow lädt
prüfsummengesperrte Eingaben, kompiliert Kernel und passende Module, installiert
frische OpenWrt-Pakete und erzeugt Installationsimage und Sysupgrade samt
Prüfsummen und Prüfberichten. Er flasht kein Gerät und veröffentlicht keine
Hardware-Stabilitätsfreigabe. Ein erfolgreicher kompletter Actions-Lauf ist der
Nachweis der CI-Build-Kette; reine Vorbereitungs-Checks sind kein Image-Build.

Profile: `base`, `base-A`, `base-B`, `base-A-B`. Basis enthält HDMI-Konsole und
Audio, Ethernet, internes WLAN, IR und Frontdisplay. A ergänzt die ausgewählten
USB-Netzwerk-/Modemtreiber; B GPU/Multimedia einschließlich Cedrus/UVC.
PCIe, MHI und NVMe bleiben ausgeschlossen. Konsolen: `dual`, `hdmi`, `uart`.
Die konkreten Pakete/Module stehen in den Artefakt-Manifesten.

Der lokale Einstieg zur gleichen Kette ist `tools/build-openwrt-release.py`.
Die getrennten Vorbereitungs- und Quellprüfungsworkflows bleiben verfügbar.
[Build-Eingaben, Signierung und Grenzen](docs/actions-build.md).

## Standardzugang

AP **openwrt**, WLAN-Passwort **openwrtopenwrt**; SSH/LuCI **root / openwrt**.
WLAN-Adresse **192.168.50.1**, Ethernet per DHCP. Nach Installation ändern.
`python3 installer/t95h.py access` bereitet eigene Zugangsdaten lokal vor;
es überträgt diese nicht automatisch als GitHub-Build-Eingabe.
[Zugangsregeln](docs/default-access.md).

## Dokumentierte Hardwarepunkte

SD-Start: eine Sekunde Wartezeit und bis zu drei MMC-Rescan-/Ladeversuche im
Bootskript; bisher zwei erfolgreiche Kaltstarts auf den ersten Versuch gemeldet.
Keine gezielte Stromschaltung, keine Bootmarker und kein Beweis vollständiger
Kaltstartzuverlässigkeit. Das Skript hilft erst, nachdem es geladen wurde.
WLAN: konsolidierter xradio-Stand mit vier u32-Leselängenkorrekturen und Firmware
.58; gelegentliche SDIO-Datenfehler/missed interrupts bleiben dokumentiert.
GPU-Initialisierung und Audio-Hardwarevalidierung bleiben ebenfalls offene
Punkte. Weitere Hör-, Belastungs- oder Hardwaretests sind derzeit nicht Teil
dieses Auftrags. Andere Linux-Distributionen werden später konkret angepasst.
