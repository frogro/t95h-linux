# Multimedia-Livetest unter OpenWrt 6.12.94

Mesa25.2.4 nutzt Mali-G31/Panfrost (OpenGL ES3.1). kmscube Offscreen und
HDMI-Ausgabe erfolgreich, HDMI etwa57,5fps. GStreamer-Konvertierung/Skalierung,
GL-upload/colorconvert/download, Opus und Theora Encode/Decode erfolgreich.
UDP/RTP-Opus und TCP auf Loopback geprüft; TCP128KiB bytegleich. Kein Nachweis
sämtlicher Plugins oder einer externen Netzwerkstrecke.

HDMI-ALSA mit Stille erreicht EOS. Analogausgabe hing bei deaktiviertem
`DAC Playback Switch` und `Line Out Playback Switch`. Nach Aktivierung beider
Schalter läuft hw_ptr von43520 auf92192 weiter und der Test erreicht nach4,267s
EOS/Exit0. Alle Mixerwerte anschließend exakt wiederhergestellt. Lautstärke blieb
0; hörbarer Analogton wurde nicht geprüft. Für neue Images ist jetzt eine begrenzte ALSA-Initialisierung integriert:
DAC/Line-Out aktiv, Stereo, DAC 63/63, Line-Out 6/31. Einstellungen stehen in
/etc/t95h-audio.conf; LibreELEC erlaubt /storage/.config/t95h-audio.conf als
persistente Überschreibung. ENABLED=0 deaktiviert sie. Die hörbare Ausgabe
mit diesen neuen Vorgaben ist noch nicht getestet.

ElgatoHD60X über USB2/480Mbit/s erkannt. V4L/GStreamer empfangen Frames,
ustreamer6.52 liefert HTTP-Snapshot, aber auch nach Anlaufphase nur die Elgato-
Fehlermeldung „Invalid output resolution selected“ (640x480 und720p). Das Gerät
verlangt laut Hersteller USB3; kein fehlerfreier Nutzbildbetrieb nachgewiesen.
V4L meldet verworfene Puffer. USB-Audiointerfaces vorhanden, aber kein ALSA-Gerät
und kein snd-usb-audio-Modul installiert. GStreamer-Pluginloader-Warnung entfällt
mit explizitem GST_PLUGIN_SCANNER=/usr/lib/gstreamer-1.0/gst-plugin-scanner;
keine Plugins auf der Blacklist. Neue Images ergänzen USB-Audio: OpenWrt 6 Profil B als kmod-usb-audio,
LibreELEC/Anotter explizit im Kernel. OpenWrt erhält den Scanner zusätzlich
am einkompilierten libexec-Pfad als Symlink. Damit sind die Paketlücken
behoben; ein erfolgreicher Elgato-Betrieb an USB2 folgt daraus nicht.

Rohprotokolle lokal unter build/sd-dram-720-test/pmic305-600-gpu960/
wlan-live-tests/media-tests/. Der SDIO-Sample-Delay-Test brachte keine Behebung;
der ursprüngliche Kernel wurde wiederhergestellt. Dieser Testpatch gehört nicht
in neue Releases.
