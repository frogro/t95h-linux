# T95H vollständiger DT-Referenzstand

`t95h-tested-full.dts` ist die eigenständige, aus der zuletzt ausgelieferten DTB abgeleitete Referenzquelle. Sie enthält alle finalen Eigenschaften einschließlich der nachträglichen Audio-, CPU/GPU-, Display-IOMMU-, IR- und Cedrus-Anpassungen. Sie ist noch das vollständige Profil, keine Basis/A/B-Aufteilung. Die ursprüngliche Board-DTS im Kernel allein erzeugt diesen nachbearbeiteten Stand nicht.

`python3 tools/build-tested-dtb.py --output /projekt/tmp/t95h.dtb` baut diese Quelle und prüft sämtliche Knoten, Eigenschaftsbytes, Speicherreservierungen und die Boot-CPU gegen die gesperrte Referenz. Benötigt dtc und Python-libfdt. Keine Box-/SD-Zugriffe.

Die neue Binärdarstellung unterscheidet sich von der durch libfdt nachbearbeiteten Referenz. 234 Knoten und 1221 Eigenschaften sind vollständig inhaltsgleich. Der Nachweis ist keine Bytegleichheit und kein neuer Hardwaretest. Für Releases ist die dtc-Version zu sperren. Phandle-Zahlen sind Referenzwerte dieses vollständigen Baums und dürfen nicht manuell umnummeriert werden.

Audio bleibt Basis: Mainline-Analogcodec mit Line-Out, AHUB-HDMI mit koordinierter PLL-/Modultaktbelegung und passendem BCLK-Treiberquirk. Optionale zusätzliche Vendor-I2S-Knoten aus dem historischen digitalen Audiopatch wurden nie integriert und werden hier nicht ergänzt. Kein Hörtest auf Benutzerwunsch; der Status bezieht sich auf Quellen, Konfiguration und gespeicherte technische Befunde, nicht akustische Bestätigung.
