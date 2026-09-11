# LibreELEC T95H – experimenteller Port

Der zweite OS-Adapter baut ein eigenes `PROJECT=T95H`, zunächst ARM64 Basis+B.
OpenWrt bleibt unverändert. `build-libreelec.yml` ist separat manuell startbar.

Jeder neue Lauf löst die neueste stabile LibreELEC-GitHub-Veröffentlichung einmal
auf und speichert Tag und Commit in `libreelec-request.json`. Keine Nightlies,
kein stiller Rückfall auf ältere Releases. Der Adapter wurde zunächst gegen
12.2.1 geprüft. Ändern sich relevante Upstream-Builddateien, stoppt die
Quellvertragsprüfung bis zur bewussten Anpassung an das neue Release.

Kernel 7.2.3, konsolidierte T95H-Patches und beide XR819-Korrekturen bleiben
fest. Die LibreELEC-H6-Kernelpatches werden nicht blind dazu gemischt.
LibreELEC baut seinen Kernel mit seiner eigenen Toolchain; Kernelmodule werden
gegen genau diesen Build gebaut. Keine OpenWrt-APK- oder Fremdkernelmodule.
Der Adapter aktiviert SquashFS, Initramfs und systemd-Anforderungen. Die
LibreELEC-FFmpeg-V4L2-Request/DRM-Prime-Pfade bleiben verfügbar; tatsächliches
Cedrus-Decoding in Kodi ist noch nicht getestet.

Die neuen systemd-Dienste übernehmen die verzögerte Regulator-/GPU-Einbindung.
UCI, procd, LuCI und OpenWrt-AP-Konfiguration werden nicht kopiert. Netzwerk
verwaltet LibreELEC; WLAN/AP-Zugang und Dienste müssen separat getestet werden.
Das bisherige 60-/120-Sekunden-Minimum wird beim ersten Port nicht verkürzt.
Kodi startet erst nach erfolgreicher GPU-Prüfung; Netzwerk bleibt unabhängig.

Actions baut zunächst KERNEL und SYSTEM, danach zwei komprimierte Rohimages:
SD und eMMC mit separaten UUIDs. Bootcode wird aus der gesperrten bestehenden
Kette übernommen; der MBR wird für 1024 MiB FAT und 512 MiB STORAGE angepasst.
Die eMMC-Variante übernimmt zusätzlich unsere geprüfte eMMC-Bootprefix- und
DTB-Transformation. Dies sind Dateiartefakte; der Workflow greift auf keine Box zu.

**Stand: Vollständiger Build erfolgreich, erster Kodi-Hardwaretest ausstehend.** Der vollständige Ausgangsbuild liegt als Actions-Artefakt vor; der Packaging-Workflow
veröffentlicht daraus Release-Kandidaten samt zusätzlicher Installations-SD.
Das separate eMMC-Rohimage ist selbst kein von SD startbarer eMMC-Installer.

Vor einer Veröffentlichung sind noch erforderlich:

- Boot von SD, HDMI/Kodi, Netzwerk, Panfrost, Audio, Cedrus und IR testen.
- Frontdisplay-Dienst und IR-Keymap auf LibreELEC übertragen.
- Neuen eMMC-Installations-SD-Adapter auf Hardware testen und einen passenden
  LibreELEC-Updateadapter erstellen. OpenWrt-sysupgrade ist ausdrücklich nicht kompatibel.
- Medienabhängigkeiten der ausgelassenen H6-Patches einzeln bewerten.
- Abhängigkeiten, Artefaktprüfungen und Lizenz-/Quellnachweise abschließen.

Die Kernelversion kann gleich bleiben, während die Kernelkonfiguration und ABI
für LibreELEC angepasst werden. Ein erfolgreicher OpenWrt-Test ersetzt keine
LibreELEC-Hardwareprüfung. Automatische Speichererweiterung ist derzeit nicht
Teil dieses Ports.

### Fortsetzbare Actions-Builds

Der Workflow verwendet bis zu drei Jobs mit jeweils eigenem Zeitlimit. Nach
180 Minuten startet der Paketplaner keine weiteren Pakete; laufende Pakete
werden beendet. Anschließend werden der vollständige LibreELEC-Baum inklusive
Toolchain, Quellen, Compiler-Cache, Paketmarkierungen und Hardware-Eingaben als
`libreelec-checkpoint-N` archiviert (7 Tage Aufbewahrung). Der nächste Job
übernimmt diesen Stand und ruft denselben inkrementellen Build auf.

Jeder Restore prüft SHA256, Repository-Commit, LibreELEC-Quellstand,
Runner-Betriebssystem, CPU-Voraussetzungen der Hostwerkzeuge und absoluten
Arbeitsverzeichnispfad. Rechte und Symlinks bleiben erhalten. Ein neuer Lauf
prüft weiterhin die neueste stabile LibreELEC-Version; eine Fortsetzung mit
einem inzwischen veralteten Quellstand wird abgewiesen.

Falls auch der dritte Job regulär pausiert, lässt sich ein neuer Lauf am selben
Commit mit `resume_run=<Run-ID>` und
`resume_checkpoint=libreelec-checkpoint-3` starten. Die vorherige Sicherung wird
übernommen. Bereits vor dieser Änderung gestartete Jobs haben keinen solchen
Checkpoint und können nicht nachträglich fortgesetzt werden.

Grenzen: Kein Checkpoint wird aus einem abgebrochenen Compilerprozess oder nach
einem echten Buildfehler erzeugt. Nach 300 Minuten beendet eine Notgrenze den
Build; ein einzelnes außergewöhnlich langes Paket kann damit weiterhin den
Job scheitern lassen. Archivierung und Upload benötigen freien Plattenplatz und
GitHub-Artefaktspeicher. Ein inkompatibler neuer Runner oder geänderte Patches
führen zu einer expliziten Ablehnung der Sicherung. Die erfolgreiche Fortsetzung bis zum fertigen Image ist mit Run 34642912252
belegt. Spätere Packaging-Aufträge können dessen fertige Eingaben nutzen.

## Vollständiger Build und eMMC-Installations-SD

Run 34642912252 hat Kernel, SYSTEM und beide Rohimages erfolgreich gebaut.
Der separate Packaging-Workflow verwendet diese fertigen Eingaben und ergänzt
nun die SD mit eMMC-Installationspartition. Kernel und Kodi werden dafür nicht
neu kompiliert. Die Anotter-DE33-Patches bleiben vorerst getrennt.
[Installationsanleitung](media-emmc-installation.md).
Die eMMC-Installation und das neue Paket müssen auf der Box getestet werden;
der erste Vergleich beginnt mit dem normalen SD-Image.
