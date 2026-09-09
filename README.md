# T95H Linux / OpenWrt

Experimentelles Build-Projekt für die T95H mit H616. Linux 7.2.3,
Board-Patches und die getestete Bootkette bleiben festgelegt. Jeder neue Auftrag
ermittelt die aktuelle stabile OpenWrt-Version einmal und baut genau ein Profil.
Kein A/B-Vergleichsbuild und keine automatischen Hardwaretests.

## Einstieg über installer.sh

Voraussetzungen auf dem ThinkPad: `git`, `gh`, `python3` und `gh auth login`
mit Berechtigung zum Workflow-Start. Das Repository ist öffentlich.
Authentifizierter Download als Alternative zu wget:

```sh
gh api -H 'Accept: application/vnd.github.raw+json' repos/frogro/t95h-linux/contents/installer.sh?ref=main > installer.sh
sh installer.sh
```

Direkter Download:

```sh
wget -O installer.sh https://raw.githubusercontent.com/frogro/t95h-linux/main/installer.sh
sh installer.sh
```

Das Skript legt einen separaten Checkout unter `~/.local/share/t95h-installer`
an, fragt Profil und Konsole ab und startet den vollständigen Actions-Build.
Vorhandene lokale Änderungen werden nicht überschrieben. Es flasht kein Gerät.
Ohne Dialog und für spätere Downloads:

```sh
sh installer.sh dispatch --profile base-A-B --console dual
sh installer.sh status
sh installer.sh releases
sh installer.sh release-download --tag t95h-RUN_ID-ATTEMPT
```

Ein erfolgreicher Build veröffentlicht ein experimentelles
Prerelease mit Installationsimage, Sysupgrade, Prüfsummen, Manifesten und diesem
Einstiegsskript. Das Release bleibt während des Uploads als Entwurf verborgen.
Download und Prüfsummenprüfung laufen über `gh`; ein Prerelease ist keine
Bestätigung vollständiger Hardwarestabilität.

## eMMC: Installation aus einem SD-System

Eine dritte SD-Partition ist nicht erforderlich. Vorgesehen ist ein System mit
FAT-Bootpartition und ext4-Rootpartition auf SD. Das Installationsprogramm gehört
in dieses Root-Dateisystem und wird bewusst gestartet, niemals automatisch beim
Einstecken oder Booten. Der ThinkPad kann den Vorgang über SSH bedienen.

Die SD muss dafür **ihr eigenes Root-Dateisystem** verwenden. Eine SD, die bereits
zur eMMC weiterleitet, ist kein Installations-/Rettungssystem zum Überschreiben
der eMMC. Vor dem Schreiben sind Board, laufendes Root-Medium, eMMC-CID, Größe,
freie Nutzung des Ziels und die Prüfsumme des passenden eMMC-Pakets zu prüfen.
SD- und eMMC-Images benötigen unterschiedliche Kennungen und Bootkonfigurationen.
Ein SD-Sysupgrade darf nicht auf eMMC angewendet werden.

**Stand:** Direkter eMMC-Boot mit Reset/FIFO-Backport wurde beobachtet. Der generische
eMMC-Release-Installer und eMMC-Sysupgrade sind noch nicht freigegeben; aktuelle
Actions-Releases enthalten das SD-Imagepaar. Die experimentellen lokalen
Installationsskripte sind kein Bestandteil des Download-Installers.

Geplanter Ablauf im selben ThinkPad-Installer: Ziel SD/eMMC wählen, SD starten,
Box-Adresse und Root-Passwort eingeben. Der Installer baut SSH selbst auf; eine
manuell geöffnete SSH-Sitzung ist nicht nötig. Nach vollständig geprüfter
Übertragung läuft der Schreibauftrag auf der Box unabhängig von der Verbindung.
Bei Wiederverbindung wird der gespeicherte Auftragsstatus abgefragt, nicht blind
noch einmal geschrieben. Vorher muss die Verbindung funktionieren; für diesen
Schritt ist Ethernet mit DHCP vorgesehen. Eine Verbindungstrennung gilt weder
als erfolgreicher Abschluss noch als Erlaubnis zum Neustart.
[Technischer eMMC-Stand](docs/emmc-installation.md).

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

## Erfolgreicher vollständiger Actions-Lauf

Der [Lauf 34363631215](https://github.com/frogro/t95h-linux/actions/runs/34363631215)
hat Basis+A+B mit dualer Konsole vollständig gebaut. Download, Image-Prüfsummen,
Kernel-APK-Signatur und das enthaltene SD-Rescan-Skript wurden anschließend auf
dem ThinkPad geprüft. [Prüfnachweis](docs/actions-validation-20260909.md).
