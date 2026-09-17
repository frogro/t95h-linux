# Bildschirmübertragung an die T95H

Du kannst den Bildschirm eines Computers über dein lokales Netzwerk auf der
T95H anzeigen. Der Computer bleibt dabei eingeschaltet und gibt seinen
Bildschirm frei. Ein HDMI-Grabber ist dafür nicht nötig.

## Weg 1: Deskreen CE im Kiosk-Browser

1. Starte Deskreen CE auf dem Computer, dessen Bildschirm du anzeigen möchtest.
2. Trage die dort angezeigte Verbindungsadresse in der `kioskbrowser.ini`
   unter `[browser]` als `url` ein und starte den Kiosk neu.
3. Bestätige die Verbindung auf dem sendenden Computer.
4. Wähle den Bildschirm oder das Fenster aus und gib es frei.

Bei einer neuen Sitzung kann Deskreen eine neue Adresse anzeigen. Übertrage
diese dann in die Kiosk-Konfiguration. Beende die Freigabe auf dem Computer,
um die Übertragung zu stoppen; für deine normale Kiosk-Webseite trägst du
wieder deren Adresse ein.

## Weg 2: go2rtc mit direkter Cedrus-Videoausgabe

Auf dem Computer erfasst ein Aufnahmeprogramm den Bildschirm und komprimiert
ihn als H.264-Video. **go2rtc** stellt diesen Stream bereit. Auf der T95H
übernimmt **Cedrus** die Dekodierung; ein Player zeigt das Bild über HDMI an.
Währenddessen pausiert der Kiosk-Browser. Die Kiosk-URL bleibt unverändert.

Die folgende Anleitung richtet diesen Weg ein. Mit `Strg+C` im Player beendest
du die Übertragung auf der Box und kehrst zur Kiosk-Webseite zurück.

## Schritt für Schritt: Linux-PC mit Intel-Grafik → T95H

Diese Anleitung verwendet Ubuntu/GNOME mit Wayland und Intel-Grafik. Windows, macOS und andere Grafikchips
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
Treiberfehler zuerst beheben.

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

Der Download ist für einen **x86-64-PC**. Für
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

Der Befehl hält den Browser an und zeigt den Stream direkt.
Mit `Strg+C` beenden; die normale Kiosk-Webseite startet wieder. Die
`kioskbrowser.ini` muss für diesen nativen Weg nicht geändert werden.

Anschließend optional VirtualHere verbinden. Soll ein lokaler Dialog an der Box
bedient werden, dort zuerst den USB-Empfänger im VirtualHere-Client freigeben.
Die Videoverbindung selbst bleibt davon unberührt.

## Optional: Maus und Tastatur mit VirtualHere

Installiere den VirtualHere USB Server auf der Box und den
[VirtualHere Client](https://www.virtualhere.com/usb_client_software) auf dem
sendenden Computer. Wähle im Client den USB-Empfänger von Maus und Tastatur
an der Box aus und verbinde ihn mit **Use**. Die Geräte bedienen nun den
sendenden Computer.

Mit **Stop Using** gibst du sie wieder für die Box frei, beispielsweise für
einen lokalen Bestätigungsdialog. Ein USB-Empfänger kann jeweils nur an einer
Seite verwendet werden. Die Bildübertragung läuft davon unabhängig weiter.

VirtualHere wird separat installiert und unterliegt den Lizenzbedingungen
des Anbieters.
