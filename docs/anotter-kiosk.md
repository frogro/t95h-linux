# T95H AnotterKiosk: erster SD-Test

Experimenteller Port von [AnotterKiosk](https://github.com/Manawyrm/AnotterKiosk),
Debian 13 (trixie), Chromium und unserem angepassten Linux 7.2.3.
Dies ist kein offiziell von AnotterKiosk unterstütztes Board. Noch kein
Hardwaretest dieses Images; eMMC-Installation und OS-Updateadapter folgen erst
nach erfolgreichem SD-Test. Nicht als OpenWrt-Sysupgrade verwenden.

Der separate Workflow `build-anotter.yml` löst beim Start die neueste stabile
AnotterKiosk-Version auf, hält deren Git-Commit für den Lauf fest und installiert
aktuelle signierte Debian-Pakete aus trixie, trixie-updates und trixie-security.
Ein Wechsel der Debian-Hauptversion muss im Adapter überprüft werden.
Kernel, Patchbasis und Bootkette bleiben fest; Basis+B wird um die Voraussetzungen
für systemd und Chromium ergänzt. OpenWrt und LibreELEC werden dadurch nicht
auf einen anderen Kernel umgestellt. Die Paketversionen, Kernelkonfiguration,
Quellversionen und Image-Prüfsummen liegen dem Artefakt bei. Identische Binärdateien
bei einem späteren Neubau sind wegen der beweglichen Debian-Paketquellen nicht garantiert.

## Build und Download am ThinkPad

```sh
python3 installer/anotter.py dispatch
python3 installer/anotter.py status
python3 installer/anotter.py download --tag anotter-RUN_ID-ATTEMPT
```

Das Release enthält ein `.img.gz` für SD, Manifest, SHA256SUMS, Paketliste und
Kernelkonfiguration. Das entpackte Image ist 6276 MiB groß; mindestens 8-GB-SD
verwenden. Mit einer Image-Schreibanwendung auf die gewünschte SD schreiben.
Dabei wird deren vorhandener Inhalt ersetzt. Das Tool `anotter.py` selbst
schreibt keine Rohdaten auf Datenträger und verändert keine eMMC.

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
Optional kann `installer/anotter.py access --boot <FAT-Pfad> --key <Schlüssel.pub>`
das Kopieren übernehmen; der manuelle Originalweg bleibt vollständig nutzbar.

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
- HDMI, Audio, GPU und Cedrus verwenden unsere T95H-Kernelbasis. Die Funktion
  unter Debian/Chromium ist noch zu testen; ein vorhandener Decoder-Treiber
  beweist keine Browser-Hardwaredecodierung.
- Panfrost startet nach der bewährten späten Regulatorinitialisierung (frühestens
  120 Sekunden). LightDM wartet auf den Grafikdienst; LAN und SSH warten nicht.
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
