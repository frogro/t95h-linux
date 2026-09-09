# Release contract for the future installer

Decision confirmed 2026-09-07: preserve the tested custom Linux 7.2.3 kernel baseline and boot chain. Do NOT automatically select the newest Linux kernel. Kernel/boot-chain updates require a separate explicit change and validation. Profiles may enable or disable optional features on that pinned source and patch baseline; their matching modules must be built from it.

Each installer job resolves the current stable OpenWrt release ONCE (not snapshots/RCs). Lock the resolved OpenWrt sources, tested kernel/boot-chain sources, commits, SHA256, toolchain, SOURCE_DATE_EPOCH, T95H patch-series revision and selected profile before building. Both independent builds and both output types consume this SAME lock. Never silently fall back on an older OpenWrt version if compatibility fails.

Installer runs on the ThinkPad and will trigger GitHub Actions, download verified results and optionally flash an explicitly identified SD. The full installer/source-build pipeline is still to be implemented.

Four profiles: base, base+A, base+B, base+A+B.
- Base: boot chain, storage/rootfs, Ethernet, internal WLAN/AP, USB core, CPU/thermal regulation, front display, HDMI console, HDMI and analog audio, matching kernel/modules, update support, package management, SSH and LuCI for OpenWrt.
- A (additional network): USB WLAN, USB Ethernet and USB modems, including corresponding firmware, userspace and management/LuCI components.
- B (multimedia): GPU/Panfrost/Mesa, Cedrus video decoding, USB UVC video capture and associated audio/video streaming userspace. Additional grabber chipset support is selected by supported device IDs; streaming does not require A. IR/other optional functions must receive an explicit profile assignment before implementation; no ambiguous “miscellaneous” toggle.
- HDMI console and audio are mandatory base features, NOT conditional on B.
- PCIe/MHI/NVMe excluded for this board.
- H616 hardware encoding is not integrated: do not offer a misleading enabled checkbox.

EVERY image release MUST contain a matching sysupgrade file, including all four profile combinations. An install-only release is incomplete and must not be published. Install and upgrade artifacts use the SAME OpenWrt version, kernel/DTB/module set, profile and source lock. Ship checksums and a build/profile manifest together. Preserve configuration and SSH host keys during upgrades; retain progress and completion verification. Explain removed functionality when changing profiles.

Keep hardware support separate from distribution integration so later Linux distributions can map A/B capabilities to their own packages. Personal SD backups and device keys are private and must never be published as release images. Preserve the last known-good release and distinguish built/tested/hardware-validated status.

Selections are resolved before compilation: a built-in kernel feature cannot be removed by uninstalling an APK. Record final Kconfig, DTB, selected packages, firmware hashes and licensing. Required hardware dependencies cannot be toggled off independently. No official OpenWrt-kernel kmods may be substituted for our custom-kernel modules. Every installer-selected OpenWrt package/module is part of the persisted selection manifest and MUST be rebuilt or resolved into the next matching upgrade. Dependencies, firmware and configuration migration are included. A missing or incompatible selection blocks the upgrade build; never silently omit it or substitute an official kmod for another kernel. Manually installed packages require explicit inventory/import into that selection before retention can be promised; sysupgrade does not retain their binaries automatically.

The local test uses OpenWrt 25.12.5 + existing custom Linux 7.2.3. It performs no kernel rebuild/version change. `package-openwrt-upgrade.py` reads release and kernel identity FROM the verified image. No 25.x upper limit is hardcoded.

Reusable workflow `package-openwrt.yml` implements the artifact packaging stage, not the still-to-be-completed entire source-build/installer pipeline. The upstream build supplies `t95h-base.img` and `host-tools/fwtool` in one trusted artifact. Pin the runner/container, e2fsprogs/Python/zlib versions and action commits for release CI; packaging records actual tool identities. Package A/B on equal tool versions must be byte-identical. Do not publish source/OS combinations as hardware-validated based on A/B equality alone.

No GitHub workflow is dispatched or release published by this local work. Before public distribution add signing/key distribution and platform tests; checksums alone provide integrity, not publisher authentication.

Confirmed 2026-09-07: base+B must be reusable for other supported Linux distributions without A. See `os-profiles.md` for the separation between hardware support and distribution adapters. This is a required architecture and validation target, not a claim that other OS images have already passed hardware tests. OpenWrt sysupgrade artifacts are specific to OpenWrt; other OS adapters must implement their own matching update mechanism.

Encoder work is deferred until the end, potentially as optional bonus profile C. C is not currently implemented/selectable and must not become a dependency of base, A or B.

Current implementation scope: OpenWrt only. Concrete other-OS adaptation and testing are deferred to a later selected example, potentially Debian/Ubuntu based. Keep hardware/OS separation, but do not block OpenWrt completion on implementing another distribution.

Release notes: use the official notes for the exact resolved OpenWrt release as an attributed source and link to their full text. Provide a concise adapted summary, then T95H-specific kernel/boot-chain changes, selected profiles, validation status, known limitations and matching install/sysupgrade assets. Do not copy official download/upgrade instructions or official kernel/security-fix claims as if they automatically apply to our custom kernel. Identify releases as unofficial T95H builds, not releases issued by OpenWrt. A new build of the same OpenWrt version needs its own T95H revision and changelog.

Profile-specific release notes are mandatory: generate the T95H additions from the final resolved build manifest, not the installer request alone. Base features appear for every profile; A/B sections appear only when actually included. A+B receives both sections. C remains absent until implemented and selected. List inclusion, build validation and hardware validation separately. For a release containing multiple profiles, use a per-profile feature/artifact table and name the corresponding install and sysupgrade pair unambiguously.

Superseding decision 2026-09-09: no second A/B build or A/B packaging run at present. One locked build must still produce and validate both install and sysupgrade artifacts. Baseline and WLAN exclusions are recorded in boards/t95h/baseline.json. The preparation workflow does not claim to build images.
