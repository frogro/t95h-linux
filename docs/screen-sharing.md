# Bildschirmübertragung an die T95H

Die normale Kiosk-Funktion zeigt Webseiten. Bildschirmübertragung benötigt
zusätzlich ein Programm auf dem Computer, dessen Bild angezeigt werden soll.
Die hier getestete Verbindung bleibt im lokalen Netzwerk. Der sendende Computer
muss eingeschaltet und die Bildschirmfreigabe aktiv sein.

## Einfacher Einstieg: Deskreen CE

Deskreen CE auf dem sendenden Computer starten. Seine lokale Verbindungsadresse
in der `kioskbrowser.ini` als `url` eintragen und den Kiosk neu starten. Verbindung
bestätigen, Bildschirm auswählen und freigeben. Die Adresse kann sich bei einer
neuen Sitzung ändern. Bei „Seite nicht erreichbar“ zuerst die Anwendung, die
aktuelle Adresse und die Erreichbarkeit im LAN prüfen.

Auf unserer T95H war dieser Weg funktional, für präzise Mausbedienung jedoch
zu träge. Der neue Displaykernel allein beseitigt diesen Engpass nicht.

## Bessere Bedienbarkeit im Test: go2rtc und Cedrus

Der getestete Aufbau besteht aus Bildschirmaufnahme und Intel-H264-Encoding auf
dem sendenden Linux-PC, [go2rtc](https://github.com/AlexxIT/go2rtc) als lokalem
Streamserver und einem nativen Player auf der Box. Der Player ersetzt während
der Übertragung den Kiosk-Browser auf HDMI. Er ist keine zweite Webseite.
Panfrost beschleunigt Grafik; Cedrus übernimmt hier die Videodekodierung.

Der aktuelle Messstand: 1080p, etwa 34–38 tatsächlich gelieferte Bilder/s,
30 ms Empfangspuffer. Die Aufnahme war auf maximal 60 fps eingestellt.
Die entscheidenden Player-Einstellungen sind:

```sh
gst-launch-1.0 rtspsrc location=rtsp://STREAMSERVER:8554/desktop \
  protocols=tcp latency=30 drop-on-latency=true \
  ! rtph264depay ! h264parse ! v4l2slh264dec \
  ! video/x-raw,format=NV12 \
  ! kmssink driver-name=sun4i-drm plane-id=35 \
    plane-properties=props,zpos=2 skip-vsync=true sync=false
```

Dies ist das dokumentierte **Testrezept**, kein universeller Installationsbefehl.
Es benötigt den passenden DE33-Kernel/DTB, GStreamer mit `v4l2slh264dec` und
`kmssink`, einen laufenden H264-Stream und exklusiven Zugriff auf die Anzeige.
Die Plane-ID muss auf anderen Builds geprüft werden. Beim Test lief RTSP über
einen lokalen SSH-Tunnel; dann ist die Adresse `rtsp://127.0.0.1:18554/desktop`.
Ein direkter LAN-Stream muss entsprechend erreichbar und gegen ungewollten
Zugriff geschützt sein. Es gibt keinen vorkonfigurierten öffentlichen Relay.

Ein neuer Freigabedialog nach dem Neustart der Aufnahme ist normal. Bricht die
Quelle ab, reicht ein Neustart des Players allein nicht: zuerst die Aufnahme
wieder freigeben. Für die Rückkehr zur normalen Webseite den Player beenden und
LightDM starten. Diese Einrichtung wird noch nicht automatisch im Image aktiviert.

## Optional: Maus und Tastatur mit VirtualHere

Auf der Box läuft der VirtualHere USB Server, auf dem sendenden Computer der
[VirtualHere Client](https://www.virtualhere.com/usb_client_software).
Dort den USB-Empfänger der Maus/Tastatur auswählen und verbinden. Beide Geräte
steuern dann den sendenden Computer über das Bild auf der Box.

Für einen lokalen „Allow“-Dialog im Kiosk den Empfänger im Client mit
**Stop Using** freigeben. Nach der Bestätigung mit **Use** wieder verbinden.
Ein Empfänger kann nicht gleichzeitig lokal und entfernt verwendet werden.
VirtualHere ist optional, nicht im Image enthalten und separat nach den
Lizenzbedingungen des Anbieters zu verwenden. Bildschirmübertragung allein
überträgt keine USB-Eingaben.

[Technische Messergebnisse](anotter-display-validation.md).

## Schritt für Schritt: Linux-PC mit Intel-Grafik → T95H

Dieser Weg entspricht dem getesteten Ubuntu/GNOME-Wayland-PC mit Intel-Grafik.
Er ist nicht an einen ThinkPad gebunden. Windows, macOS und andere Grafikchips
benötigen eine andere Aufnahme-/Encoder-Einrichtung; die folgenden Befehle
sind dafür nicht unverändert gedacht. Ton wird hier nicht übertragen.

### 1. Auf dem sendenden PC installieren

Unter Ubuntu/Debian:

```sh
sudo apt update
sudo apt install ffmpeg python3-gi gir1.2-gstreamer-1.0 \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-pipewire pipewire xdg-desktop-portal xdg-desktop-portal-gnome \
  intel-media-va-driver vainfo openssh-client wget
```

Das Paket für das Desktop-Portal muss zur Oberfläche passen; oben steht die
GNOME-Variante. Diese Anleitung setzt eine laufende **Wayland-Desktopsitzung**
voraus. Die Aufnahme als normal angemeldeter Benutzer starten, nicht mit sudo
und nicht aus einer reinen SSH-Sitzung. Mit `vainfo --display drm --device
/dev/dri/renderD128` prüfen, ob H264-Encoding verfügbar ist; Zugriffs- oder
Treiberfehler zuerst beheben. Auf dem Test-PC war ein passender Intel-iHD-Treiber
nötig. Dessen lokaler Sonderpfad wird nicht allgemein vorausgesetzt.

Die Programme haben unterschiedliche Aufgaben: **PipeWire/GStreamer** erfasst
den freigegebenen Bildschirm, **FFmpeg/Intel VAAPI** komprimiert das Bild,
**go2rtc** stellt den Stream bereit. Auf der Box übernimmt **Cedrus/GStreamer**
Dekodierung und Ausgabe. VirtualHere ist davon unabhängig.

### 2. Dateien und go2rtc herunterladen

```sh
mkdir -p ~/t95h-screen
cd ~/t95h-screen
wget -O capture.py https://raw.githubusercontent.com/frogro/t95h-linux/main/examples/screen-sharing/capture.py
wget -O go2rtc.yaml https://raw.githubusercontent.com/frogro/t95h-linux/main/examples/screen-sharing/go2rtc.yaml
wget -O go2rtc https://github.com/AlexxIT/go2rtc/releases/download/v1.9.14/go2rtc_linux_amd64
chmod +x go2rtc
./go2rtc -config go2rtc.yaml
```

Das ist die im Test verwendete go2rtc-Version für einen **x86-64-PC**. Für
ARM-PCs die passende Datei aus den [go2rtc-Releases](https://github.com/AlexxIT/go2rtc/releases)
verwenden. Das Terminal geöffnet lassen. Die beiliegende Konfiguration bindet
Stream und API nur an den eigenen PC; die Box erreicht sie über SSH.

### 3. Bildschirm freigeben

In einem zweiten Terminal auf demselben PC:

```sh
cd ~/t95h-screen
python3 capture.py
```

Im erscheinenden Dialog den Bildschirm auswählen und freigeben. Die Ausgabe
`MEASURE` zeigt die tatsächlich erfassten Bilder pro Sekunde. Maximal 60 ist die
Vorgabe; abhängig vom PC können weniger Bilder geliefert werden. Das Schließen
dieses Prozesses beendet die Freigabe. Für den nächsten Start erneut bestätigen.

### 4. Mit der Box verbinden und Bild anzeigen

Im dritten Terminal, `BOX-IP` durch die Adresse der T95H aus dem Router ersetzen:

```sh
ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 \
  -R 127.0.0.1:18554:127.0.0.1:8554 root@BOX-IP
```

In dieser SSH-Sitzung auf der Box:

```sh
t95h-desktop-view
```

Dieser Befehl ist ab dem neuen **DE33-Anotter-Release** enthalten. Er prüft die
benötigten GStreamer-Elemente, hält den Browser an und zeigt den Stream direkt.
Mit `Strg+C` beenden; die normale Kiosk-Webseite startet wieder. Die
`kioskbrowser.ini` muss für diesen nativen Weg nicht geändert werden.
Auf älteren Images ist der Befehl noch nicht vorhanden.

Anschließend optional VirtualHere verbinden. Soll ein lokaler Dialog an der Box
bedient werden, dort zuerst den USB-Empfänger im VirtualHere-Client freigeben.
Die Videoverbindung selbst bleibt davon unberührt.
