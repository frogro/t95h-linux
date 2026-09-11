# Experimental Anotter DE33 scaler test

Promoted to the next Anotter test build after live NV12 tests. OpenWrt and
LibreELEC profile sources remain unchanged. See docs/anotter-display-validation.md.

Baseline: repository locked Linux 7.2.3 source replay, including both XR819
incremental patches. Config derived with tools/anotter/build.py from base-B.
Unique release: 7.2.3-t95h-anotter-de33-test1.

## Source provenance

Jernej Skrabec's development branch:
https://github.com/jernejsk/linux-1/tree/h616-de33-series-rewrite-v2

Selected contiguous series: 750ef2c186e3 through 39deebbf693e (23 commits),
covering coefficient fixes, per-channel scaler descriptions, VSU8/edge
scalers, register shadows, hardware RCQ, scaler activation and VI alpha.
Full commit IDs and original patches are stored beside this file.

Additional fixes:
- 9db28cb27cf6: shared DMA domain (planes/mixer parts only; writeback not included).
- 3edf4dae0b03: XRGB UI alpha.
- ba303c2f0f7b: subsampled VI buffer alignment.
- 6c281c7aa9eb: disable planes when their CRTC is disabled.

Adaptation uses a three-way source comparison. A preliminary patch-only
application produced rejected/ambiguous hunks and was discarded. The final
patch is generated from the reviewed merged files, applies with fuzz=0,
and its resulting files are hash-checked before compilation.

Preserved T95H baseline differences: syscon plane-mapping lookup and existing
driver registration. Adopted upstream YUV capability tracking, RCQ initialization
and blender initialization. No AFBC, writeback or HDMI color-depth expansion.

DTB: move the existing IOMMU master-0 reference from mixer@280000 to the shared
planes@100000 device, matching shared framebuffer/RCQ DMA allocation. All other
DTB properties retained from the installed boot DTB (including original thermal
settings; previous thermal experiment affected only the current running boot).

## Existing measurement and test criteria

Cedrus v4l2slh264dec works; current DRM planes advertise RGB only. Decoder emits
NV12_32L32. Native display through glimagesink achieved only about 11.4 fps in
the isolated live test. Browser remains go2rtc H264 1080p15 with Intel encoding
on the ThinkPad.

After boot: verify unique kernel release, HDMI/Panfrost, absence of RCQ/IOMMU
faults, advertised DRM YUV formats, then a bounded native H264 test. Determine
whether tiled-to-linear conversion is needed; scaler support alone does not
prove zero-copy decoding or lower latency. Compare live output only after the
build has finished and with matching input settings.

Installation and hardware results must be recorded separately; compilation
success is not hardware validation.
