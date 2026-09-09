# t95h-linux (Entwurf)

Ein gemeinsamer Board-Unterbau für die T95H/H616, getrennte Buildrezepte für OpenWrt und später gegebenenfalls LibreELEC oder DietPi.

Der Installer soll OS und unterstützte Variante auswählen, einen GitHub-Actions-Workflow starten und das neu erzeugte Image samt Prüfsumme abrufen. Bei OpenWrt wird vor jedem neuen Auftrag die aktuelle stabile Veröffentlichung ermittelt und anschließend als konkrete Version mit unveränderlichen Eingangsprüfsummen gesperrt. Zwei Builds desselben Auftrags nutzen denselben Lock; ein späterer Auftrag darf eine neue Stable-Version verwenden.

Gemeinsam: geprüfter BROM/TOC0/SPL/TF-A/U-Boot-Unterbau, Boarddaten und getestete Hardware-Patches. Pro OS: Kernelkompatibilität, Rootfs, Bootargumente, init, Paketquellen und Tests. Die erfolgreiche OpenWrt-Kombination belegt nicht automatisch LibreELEC oder DietPi; insbesondere Multimedia benötigt eigene Validierung.

GitHub-Vorbereitung: Quellprüfung und Stable-Auflösung sind implementiert; ein vollständiger Image-Build und Flash-Installer fehlen noch. Vorrang hat der lokale OpenWrt-Kandidat im übergeordneten Projekt. Private SSH-/Signierschlüssel und Images werden nicht ins spätere Quellrepository aufgenommen.

## Implementierter lokaler Verpackungsschritt

`tools/package-openwrt-upgrade.py` erzeugt aus einem bereits geprüften T95H-FAT-Image ein übereinstimmendes Installationsimage und Sysupgrade-Paket. `tools/test-openwrt-upgrade.py` prüft auf lokalen Dateien; `tools/prepare-openwrt-upgrade-test.py` überträgt zur Box und führt ausschließlich die Vorprüfung `sysupgrade -T` aus. `.github/workflows/package-openwrt.yml` ist die wiederverwendbare CI-Verpackungsstufe, noch kein kompletter Betriebssystem-Build.

`tools/resolve-stable-versions.py` liest die offiziellen Stable-Versionen. Anforderungen an Board-Patches, wählbare Treiber-/Multimedia-Profile und den vollständigen Build-Lock stehen in `docs/release-contract.md`.

## Stand 2026-09-09: konservative Grundlage

`boards/t95h/baseline.json` hält die Auswahl fest: Linux 7.2.3 bleibt gepinnt,
OpenWrt wird pro Auftrag neu auf stable aufgelöst. Basis+A+B ist vorausgewählt;
Basis, Basis+A und Basis+B sind ebenfalls für die Vorbereitung wählbar.
Es gibt vorerst keinen zweiten A/B-Vergleichsbuild.

WLAN: konsolidierter xradio-Quellstand plus vier isolierte u32-Leselängenkorrekturen.
Der Regressionstest prüft die echten Funktionen aus dem gesperrten Quellpatch.
Keine Übernahme der experimentellen 40-mA-/PG10-/1-Bit-/Firmware-.65-Änderungen.
SDIO-Datenfehler sind weiterhin ungelöst; diese Auswahl ist keine Stabilitätsfreigabe.

### Vom ThinkPad

```sh
python3 installer/t95h.py dispatch --profile base-A-B --console dual
python3 installer/t95h.py status
python3 installer/t95h.py download --run-id RUN_ID
```

Dies startet aktuell nur Quellprüfung und Release-Auflösung in Actions und lädt
Vorbereitungsberichte herunter. Es erstellt noch KEIN Image. Der separate
wiederverwendbare Verpackungsworkflow erstellt aus einem gesperrten Basisimage
Installationsimage und Sysupgrade in einem Durchlauf.

Noch zu ersetzen: die lokale Abhängigkeit von einem Vorgängerimage. Bootquellen,
Toolchain, Firmware/Lizenzen, Profil-DTS, Dienste und OpenWrt-Pakete müssen zu einem
vollständigen eigenständigen Build verbunden werden. Widersprüchlich gelesene alte
Artefakte werden nicht als Release-Ausgangsbasis hochgeladen.
