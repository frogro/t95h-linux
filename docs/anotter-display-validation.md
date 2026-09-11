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
