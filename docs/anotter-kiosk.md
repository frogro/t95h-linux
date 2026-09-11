# T95H AnotterKiosk: erster SD-Test

Experimenteller Port von [AnotterKiosk](https://github.com/Manawyrm/AnotterKiosk),
Debian 13 (trixie), Chromium und unserem angepassten Linux 7.2.3.
Dies ist kein offiziell von AnotterKiosk unterstütztes Board. Boot, Webseiten,
SSH, USB-Eingabe und Panfrost wurden auf einer T95H getestet. Jedes neue Image
bleibt bis zum eigenen Test experimentell; Eine zusätzliche Installations-SD für eMMC wird angeboten; deren
Hardwaretest und ein OS-Updateadapter stehen separat an. Nicht als OpenWrt-Sysupgrade verwenden.

Der separate Workflow `build-anotter.yml` löst beim Start die neueste stabile
AnotterKiosk-Version auf, hält deren Git-Commit für den Lauf fest und installiert
aktuelle signierte Debian-Pakete aus trixie, trixie-updates und trixie-security.
Ein Wechsel der Debian-Hauptversion muss im Adapter überprüft werden.
Kernel, Patchbasis und Bootkette bleiben fest; Basis+B wird um die Voraussetzungen
für systemd und Chromium ergänzt. OpenWrt und LibreELEC werden dadurch nicht
auf einen anderen Kernel umgestellt. Die Paketversionen, Kernelkonfiguration,
Quellversionen und Image-Prüfsummen liegen dem Artefakt bei. Identische Binärdateien
bei einem späteren Neubau sind wegen der beweglichen Debian-Paketquellen nicht garantiert.

## Download und Installation

Das passende SD-Image unter [Releases](https://github.com/frogro/t95h-linux/releases)
herunterladen, entpacken und mit einem Image-Schreibprogramm auf die gesamte
SD-Karte schreiben. Die [Schrittfolge in der README](../README.md#image-herunterladen-und-auf-sd-schreiben)
beschreibt diesen Vorgang. GitHub-Konto, Build-Installer und ein bestimmter
Host-Computer sind dafür nicht erforderlich.

Das Release enthält ein `.img.gz` für SD, Manifest, SHA256SUMS, Paketliste und
Kernelkonfiguration. Das entpackte Image ist 6276 MiB groß; mindestens 8-GB-SD
verwenden. Mit einer Image-Schreibanwendung auf die gewünschte SD schreiben.
Dabei wird deren vorhandener Inhalt ersetzt. Die SD-Installation verändert die eMMC nicht.

## SSH: unverändert wie bei AnotterKiosk

Die Einrichtung funktioniert von Windows, macOS und Linux aus. Weder ein
ThinkPad noch Python, GitHub CLI oder unser Installer sind dafür erforderlich:

1. Image herunterladen und auf SD schreiben.
2. SD erneut am Computer anschließen und die FAT32-Partition `T95HKIOSK` öffnen.
3. Dort eine Textdatei **`authorized_keys`** (ohne `.txt`) anlegen. Den öffentlichen
   SSH-Schlüssel hineinkopieren, jeweils einen vollständigen Schlüssel pro Zeile.
   Der private Schlüssel bleibt auf dem eigenen Computer.
4. Bei Bedarf die Startseite in `kioskbrowser.ini` unter `[browser] url` ändern.
5. SD sicher entfernen, in der T95H starten und LAN anschließen. Die per DHCP
   vergebene IP im Router ablesen; Anmeldung mit `ssh root@<IP>` oder einem
   SSH-Client mit demselben privaten Schlüssel. Auch der Upstream-Benutzer `pi`
   erhält die eingetragenen öffentlichen Schlüssel.

Ohne vorhandenen Schlüssel lässt sich beispielsweise mit `ssh-keygen -t ed25519`
einer erzeugen. Die `.pub`-Datei enthält den einzutragenden öffentlichen Schlüssel.


Wir übernehmen diese drei Dateien direkt und unverändert aus dem für den Build
aufgelösten AnotterKiosk-Release:

- `usr/bin/kiosk-ssh-keys`: erzeugt beim ersten Start RSA- und ED25519-Hostschlüssel
  auf FAT und kopiert `authorized_keys` nach `/root/.ssh` und `/home/pi/.ssh`.
- `etc/systemd/system/kiosk-ssh-keys.service`: führt die Einrichtung vor SSH aus.
- `etc/ssh/sshd_config.d/kiosk.conf`: `PasswordAuthentication no` und
  `PermitRootLogin prohibit-password`; ausschließlich Schlüsselanmeldung.

Es gibt kein vorgegebenes SSH-Passwort. Hostschlüssel entstehen individuell auf
der Box und bleiben bei Neustarts erhalten. Der Build überprüft, dass die drei
Dateien unverändert übernommen wurden und keine privaten Hostschlüssel oder
`authorized_keys` im öffentlichen Image liegen.

[Originalanleitung](https://github.com/Manawyrm/AnotterKiosk/blob/v0.5.8/README.md#installation)
und [Original-SSH-Skript](https://github.com/Manawyrm/AnotterKiosk/blob/v0.5.8/kiosk_skeleton/usr/bin/kiosk-ssh-keys).

Rootfs und FAT sind im Betrieb überwiegend schreibgeschützt eingebunden;
Chromium-Profil und Cache sind flüchtig. Für neue SSH-Hostschlüssel bindet
AnotterKiosk FAT kurzzeitig schreibbar ein. LAN und SSH warten nicht auf den
Grafikstart. Die Kiosk-/SSH-Konfiguration verwendet die normale FAT-Dateistruktur.

## Umfang und offene Hardwarepunkte

- Beide USB-Buchsen sind Hostports, etwa für Tastatur, Maus und USB-Touch.
- HDMI, Audio, GPU und Cedrus verwenden unsere T95H-Kernelbasis. Panfrost und native Cedrus-Ausgabe
  wurden unter Debian getestet; ein vorhandener Decoder-Treiber
  beweist keine Browser-Hardwaredecodierung.
- Panfrost startet nach der bewährten späten Regulatorinitialisierung (frühestens
  45 Sekunden). LightDM wartet auf den Grafikdienst; LAN und SSH warten nicht.
- Internes XR819-WLAN ist für den ersten Test im DT deaktiviert. Es wird kein AP
  eingerichtet. Anschluss zunächst per Ethernet. Zusätzliche Profil-A-Treiber
  und ein eigener Frontdisplay-Dienst sind noch nicht Teil dieses Kiosk-Ports.
- Etwa 1 GB RAM begrenzt anspruchsvolle Webseiten. Erste Prüfung: Boot, LAN/SSH,
  HDMI, Eingabegeräte und eine einfache Chromium-Seite.
- Bootloader-/Firmware-Provenienz und bekannte T95H-Bootprobleme gelten weiterhin;
  siehe die bestehenden Hardware- und Quellherkunftshinweise im Repository.

### Erster SD-Test und kleine Adapterkorrekturen (11.09.2026)

Der erste Test bestätigt Debian-Boot, LAN/SSH, HDMI, LightDM/Chromium und
Mesa/Panfrost als beschleunigten GL-Renderer. Chromium lief zunächst trotzdem
mit `--disable-gpu`: `pi` konnte die FAT-Konfiguration wegen `umask=0077`
nicht lesen. Die Zugriffsregelung wurde anschließend im Adapter korrigiert. Chromium startet
über das unveränderte Originalskript mit hardware_accel=1 und öffnet den
Panfrost-Renderknoten. Das ist kein Nachweis für Video-Hardwaredecodierung.

Der Adapter behält den Original-Netzwerkweg über ifupdown bei und maskiert den
zusätzlichen globalen dhcpcd-Dienst. Andernfalls verwalten zwei Instanzen eth0
und können zwei DHCP-Adressen beziehen. `/var/lib/dhcpcd` erhält wie die anderen
flüchtigen Zustandsverzeichnisse ein tmpfs; das Rootfs bleibt schreibgeschützt.

Die Original-Chromium-Startparameter versuchen bereits, Übersetzung auszuschalten.
Für die getestete Debian-Chromium-Version ergänzt der Adapter ausschließlich
`TranslateEnabled=false` in `/etc/chromium/policies/managed/t95h-kiosk.json`.
Browserstart und übrige Optionen bleiben vom Upstream übernommen.

Die FAT-Dateien bleiben standardmäßig nur für root lesbar (`fmask=0177`);
Verzeichnisse sind durchsuchbar (`dmask=0066`). Ein kleiner T95H-Dienst stellt
nur kioskbrowser.ini, splash.png und optional www-public als lesbare, schreibgeschützte
RAM-Kopien unter ihren unveränderten Originalpfaden bereit. Private SSH-Schlüssel
bleiben geschützt; Lesbarkeit für pi und fehlender Schlüsselzugriff wurden live geprüft.
Änderungen an diesen Dateien auf der SD werden beim nächsten Start übernommen.
Für Änderungen im laufenden Betrieb müssen die öffentlichen Bind-Mounts zuerst
abgehängt und danach mit t95h-public-boot.service erneut eingerichtet werden.

`examples/kiosk-test/index.html` enthält eine kleine lokale Testseite für Farben,
Animation, Maus/Touch/Tastatur und eine WebGL-Rendereranzeige. Sie ist kein Lasttest.
Die Testsitzung verwendet sie über den Original-nginx-Pfad unter www-public;
die allgemeine Release-Startseite bleibt die von AnotterKiosk vorgegebene URL.

### T95H startup and writable runtime state

The adapter keeps ifupdown as the sole Ethernet manager and selects `duid ll`
for dhcpcd. Its DHCP identity is derived from the interface MAC instead of a
new timestamp in the RAM-backed lease directory. This does not force a fixed
IP address; the router still assigns the lease. Existing DUID files take
precedence until the next boot clears the runtime directory.

The original ntpdate service and server list remain in use. A bounded preflight
waits for a default route and working DNS before invoking it; upstream retry
behavior remains active when offline. No public DNS server is hardcoded.

LightDM cache, greeter data, utmp and the Xsession log are prepared in RAM before
the display manager starts. The SD root filesystem stays read-only. The original
kiosk start page, SSH-key provisioning remain unchanged. The hardware startup timing is described below. The live service test passed; repeated-boot DHCP identity verification
remains a hardware follow-up. The optional AccountsService warning is not a GPU
failure and is not hidden by installing another account-management service.


### Faster Anotter hardware startup, tested 2026-09-11

Anotter now loads the regulator at 30 seconds and the ANA/Panfrost provider at
45 seconds. Voltage and render-node checks are unchanged. Three completed test
boots reached GPU readiness at 45.49, 45.38 and 46.14 seconds; LightDM autologin
followed at approximately 55 seconds. Chromium opened renderD128 on all three.
The last was a power-cycle test, but required two power-on attempts. The first
attempt did not consume the one-shot test configuration; its failure point is
unknown. These results do not prove reliable cold boot or long-term stability.
The early deferred-probe -110 warning remains before the successful GPU probe.
OpenWrt and LibreELEC timing is unchanged. Reverting the two Anotter wait_age
values to 60 and 120 restores the previous startup timing.

## INI-Datei über SSH dauerhaft bearbeiten

Am einfachsten lässt sich die Datei bei ausgeschalteter Box auf der SD am
Computer bearbeiten. Alternativ als root über SSH:

```sh
umount /boot/firmware/kioskbrowser.ini
mount -o remount,rw /boot/firmware
cp /boot/firmware/kioskbrowser.ini /boot/firmware/kioskbrowser.ini.bak
nano /boot/firmware/kioskbrowser.ini
sync
mount -o remount,ro /boot/firmware
systemctl restart t95h-public-boot.service
systemctl restart lightdm
```

Falls `nano` nicht vorhanden ist, einen vorhandenen Editor verwenden. Die
Öffentlichkeitskopie im RAM ist absichtlich nur lesbar eingebunden. Deshalb
zuerst den Datei-Bind-Mount lösen. Ein direktes Ändern von
`/run/t95h-public-boot/kioskbrowser.ini` wäre nur vorübergehend bis zum Neustart.
Der letzte Befehl startet Browser und Bildschirmoberfläche neu, nicht die Box.

## Neues DE33-Testbuild

Das nächste Anotter-Release enthält den auf der Box getesteten DE33-Kernel
mit passender Device-Tree-Anpassung und der Prüfung bereits geladener
GPU-Abhängigkeiten. Die übliche Webseite und die SSH-Einrichtung bleiben erhalten.
Die direkte Bildschirmübertragung ist separat einzurichten; Chromium erhält
dadurch nicht automatisch Hardware-Videodekodierung.
[Messungen und Grenzen](anotter-display-validation.md),
[Bildschirmübertragung](screen-sharing.md).

## eMMC

Die zusätzliche `sd-emmc-installer`-Variante enthält das passende eMMC-Paket.
[Installation und Einstellungsübernahme](media-emmc-installation.md).
