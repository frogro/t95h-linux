# Separates OpenWrt-Modulfeed-Testrelease

Der Workflow `Build T95H install image and sysupgrade` hat den optionalen Schalter
`module_feed_test`. Standard: aus. Bei aktivem Schalter entsteht ein eigenes
Prerelease `t95h-feedtest-<Run-ID>-<Versuch>`; das normale Release wird nicht ersetzt.

## Testumfang

Zwei echte Modul-Pakete werden aus demselben Build ausgelagert:

- `kmod-veth` mit `veth.ko`
- `kmod-sched-cake` mit `sch_cake.ko`

Diese beiden Dateien und ihre virtuellen Provider fehlen absichtlich im
Testimage. Die übrigen Router-Basismodule bleiben enthalten. Vor der Auslagerung
müssen Konfiguration, Moduldateien und Vermagic die vorhandenen Prüfungen bestehen;
kein verbleibendes Modul darf von den ausgelagerten Modulen abhängen.

Das Release enthält die SD-/eMMC-Testartefakte, die beiden signierten APKs,
`packages.adb` (signiert), öffentlichen Prüfschlüssel, Prüfsummen und
`module-feed.json`. Es ist noch kein vollständiger Feed für den gesamten
OpenWrt-Modulkatalog.

## Automatische Konfiguration

Im Testimage:

- `/etc/apk/repositories.d/99-t95h-module-test.list`: feste HTTPS-Adresse
  `https://github.com/frogro/t95h-linux/releases/download/t95h-feedtest-<Run-ID>-<Versuch>/packages.adb`
- `/etc/apk/keys/t95h-build.pem`: öffentlicher Prüfschlüssel.

Die Module verlangen sowohl die exakte `t95h-kernel`-Paketversion als auch einen
virtuellen ABI-Provider aus den SHA256 von Kernel-Image und Kernelkonfiguration.
Gleiches `uname -r` allein genügt nicht. Es gibt keinen Verweis auf `latest`.
Das Image darf erst nach vollständiger Veröffentlichung dieses Releases für den
Downloadtest verwendet werden. Die Feed-Adresse nicht auf andere Images kopieren.

## Test auf der Box

Zuerst dieses spezielle Image von SD starten. Dann:

```sh
apk update
apk add kmod-veth kmod-sched-cake
modprobe veth
modprobe sch_cake
lsmod | grep -E 'veth|sch_cake'
```

Die eigentliche VETH-/CAKE-Funktion wird danach separat getestet. Keine
Konfiguration der laufenden Netzwerkverbindung automatisch ändern. Insbesondere
kein `tc`-Shaping auf der SSH-Verbindung ohne vorbereiteten Rückweg aktivieren.

## Automatische Nachweise

Der Paketierungsschritt startet einen ausschließlich lokalen HTTP-Server und
benutzt den echten ImageBuilder-APK-Paketmanager mit isolierten Root-Verzeichnissen:

1. Neues Kernelpaket installieren; die beiden optionalen Module müssen fehlen.
2. Module aus dem signierten HTTP-Feed installieren; alle Modulbytes vergleichen.
3. Module entfernen; Kernel-Image muss unverändert bleiben.
4. Installation bei gleicher Paketversion, aber falscher ABI-Kennung ablehnen.
5. Index ohne vertrauenswürdigen Schlüssel als unvertrauenswürdig ablehnen.

Der private Schlüssel wird nicht ins Image oder Release kopiert. In den
isolierten Tests wird `--force-non-repository` ausschließlich zum Einspielen der
lokalen Kernel-Testpakete benutzt, nicht zum Umgehen von Signatur- oder
ABI-Prüfungen. Der Moduldownload selbst erfolgt regulär aus dem Feed.

Lokal: 78 Tests und zusätzlich der echte APK-HTTP-Integrationstest mit synthetischen,
nicht ladbaren Nutzdaten bestanden. Wiederholbar mit:

```sh
python3 tests/integration/module_feed_apk.py --imagebuilder /pfad/zum/imagebuilder
```

Actions wiederholt den Download-/Entfernungs-/Ablehnungstest mit den tatsächlich
gebauten Kernel- und Moduldateien. Das Laden auf Hardware bleibt ungetestet, bis
der SD-Test ausgeführt wurde. Ein allgemeiner Feed-/Paketmigrationsmechanismus bei
Updates älterer Installationen ist nicht Teil dieses ersten Experiments.
