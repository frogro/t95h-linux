# Erste aufgelöste Profil-Konfigurationen

Entwürfe, keine Releasefreigabe. Mit dem frisch wiederhergestellten Linux-7.2.3-Quellbaum und dem bisherigen GCC-14.4.0-Toolchain durch `make olddefconfig` aufgelöst. Alle angeforderten Schalter und geprüften Basisfunktionen erfüllt; kein Kernel/Image kompiliert.

Basis entfernt zusätzliche USB-Netzwerk-/Modemtreiber und deren eingebettete Firmware sowie Panfrost/Cedrus. Internes XR819-WLAN und Regulatory-Daten bleiben erhalten. A übernimmt die vorhandenen zusätzlichen USB-Netzwerktreiber und ergänzt RTL8152. B aktiviert zusätzlich UVC-USB-Videoaufnahme mit automatisch aufgelösten Videobuf-Abhängigkeiten. Audio und DRM-Anzeige verbleiben immer in Basis. PCIe/NVMe/MHI bleiben deaktiviert.

Die Entwürfe starten vom gesicherten vollständigen Kernelconfig-Stand. Sie ersetzen noch nicht den vollständigen Abgleich der anwendbaren OpenWrt-Standardfunktionen. Der jeweilige tatsächliche Modul-/Builtin-Bestand und die Paket-Provides müssen nach dem Build geprüft werden. Streaming-Pakete und zusätzliche Grabber-Chipsätze sind noch nicht vollständig aufgelöst. Ebenso sind profilabhängige DTB-/Runtime-Auswahl und externe Module noch zu verbinden. Referenz-Firmwarepfade sind beim späteren Build aus dem Firmware-Lock bereitzustellen.
