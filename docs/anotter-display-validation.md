# Anotter display test, 11 September 2026

## Accepted runtime state

User confirmed the direct Cedrus display was better controllable than Deskreen CE.
Test kernel: `7.2.3-t95h-anotter-de33-test1`, Image SHA256
`eb11982797032bf61963d4ecaece924f780ac84a66e1a841dead5366bb32f93b`.
DTB SHA256 `5314bbdcacc1492053ecec30707ce6ab404cd55046eea72dffb22137c4049d7a`.
The original boot pair remains on the running test SD for its next reboot;
this live test alone did not make the new kernel persistent.

- Intel VAAPI H264 encoding on the sending computer, 1920×1080, requested 60 fps,
  12 Mbit/s, no B frames, embedded DMZ-White cursor.
- Actual capture and display about 34–38 fps; 60 unique frames/s was not established.
- RTSP/TCP over the local SSH tunnel; receive buffer 30 ms, drop-on-latency.
- Cedrus `v4l2slh264dec` with explicit linear NV12 output, directly to KMS.
- `kmssink skip-vsync=true sync=false`, tested plane 35, zpos 2.
- VirtualHere forwards the USB receiver to the sending computer independently.

Explicit NV12 eliminated the expensive tiled-to-linear CPU conversion. The
previous conversion pipeline delivered about 2.7 fps at nearly one CPU core.
`skip-vsync=true` removed an additional display wait and gave the largest
subjective improvement. This is a GStreamer/DRM setting, not a global GPU or
Chromium setting. It trades synchronization for latency; residual streaks and
judder remain possible. No measured end-to-end latency claim is made.

The 720p/60 variant did not eliminate streaks. A 5 ms receive buffer made the
picture worse; 15 ms was inconclusive and the accepted state returned to 30 ms.
The 60 fps output in some tests included repeated source frames. Copying
PipeWire buffers did not establish an improvement.

## Deskreen comparison

With the same running test kernel, the user saw fewer streaks but unusable mouse
control. Chromium used Panfrost render nodes but no Cedrus video device was
observed in the inspected processes. CPU load was high, temperature about 70°C,
and CPU maximum frequency 408 MHz. VirtualHere remained connected.
The direct Cedrus path was restored. Thermal limits were not raised.

Later the host encoder exited with Broken pipe. The native player reached EOS
and the browser returned to an obsolete Deskreen URL. Restarting host capture
and approving the portal restored the stream; restarting the player confirmed
about 34 fps, zero reported sink drops. A process being active or a monitor
being black alone was not treated as proof of GPU failure.

## Release scope

The next Anotter build uses the exact hash-locked merged DE33 files tested above,
paired with the IOMMU master-0 binding moved from mixer to shared planes. The
GPU startup service accepts an already verified Panfrost/provider binding instead
of inserting it again. Regulator checks and thermal settings are retained.
The source adaptation is recorded in `boards/t95h/anotter/de33`.

Native video testing does not validate Chromium hardware decoding, Kodi playback,
every monitor, audio synchronization, 60 fps, or repeated cold boots. OpenWrt and
LibreELEC keep their existing kernels pending their own tests. The completed
LibreELEC baseline build is run 34642912252 and is the first Kodi test candidate.

## Local test-page animation, 17 September 2026

The original CSS `left` animation caused 61.1–65.4% aggregate CPU busy on the
Anotter live system; disabling it reduced that to 1.5%. The test page now uses
`transform: translateX()` with a compositor hint. Its travel distance is computed
on initial layout and resize, preserving the original track boundaries.

After settling: transform enabled 35.7% at 408 MHz; disabled 1.3% at 720 MHz;
re-enabled 44.4% at 720 MHz. CPU temperature was about 63–64 °C while animating.
These are short /proc/stat samples with active thermal regulation, not a fixed-
frequency benchmark. The change reduces observed CPU load but does not eliminate
browser/compositor overhead or prove browser animation frame rate. JavaScript
syntax checked; served page checked; change persisted on the personal test SD.

## Governor and browser capability audit, 17 September 2026

Chromium SystemInfo reported ANGLE OpenGL ES on Mesa Panfrost with GPU
compositing, rasterization and WebGL enabled. Video decoding and encoding were
reported as `disabled_software`; accelerated graphics do not establish hardware
video decoding. This agrees with the earlier Deskreen observation above, while
the separate native GStreamer path did demonstrate Cedrus H.264 decoding.

Short tests of the same animated page measured aggregate CPU busy of 34.0%
with performance and 33.9% with ondemand, both near 65 degrees C and already
thermally limited. These samples do not establish a long-term governor benefit.
Performance was restored after the test.

The next Anotter kernel includes CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y, making
schedutil available for a comparative live test. The existing default governor
remains unchanged until that test. The same kernel feeds the SD image and the
combined SD/eMMC installer and their update payloads. The kernel build checks
that requested enabled symbols survive olddefconfig.

Live thermal trip points were CPU passive 60/70 degrees C, GPU passive 65
degrees C, and critical 110 degrees C. No thermal threshold was changed. The
critical trip is not a validated continuous operating temperature.

## Accepted CPU trips: 70/75 degrees C, 17 September 2026

After the short live comparison, the user selected passive CPU trips of 70/75
degrees C for subsequent Anotter images and the native go2rtc/Cedrus test path.
The Anotter DTB adapter changes only those two temperatures. GPU trips, CPU
critical 110 degrees C, hysteresis, voltages and cooling maps are preserved.
The adapted DTB is included in the SD build before eMMC/installer and update
payloads are derived. OpenWrt and LibreELEC are outside this change.

In 120 seconds of browser animation, CPU temperature was 67.7–70.3 degrees C;
20 of 24 samples showed 1512 MHz, the remainder 720/936 MHz. A subsequent
60-second four-worker CPU load reached 68.7–70.1 degrees C at 480–720 MHz.
No reboot or failed service occurred; the known WLAN missed interrupts remained.
This is a short comparison, not long-term stability certification or a new
Cedrus playback result. Live 70/75 was reapplied after the comparison; it lasts
until reboot on the existing image. New builds carry the values in their DTB.
