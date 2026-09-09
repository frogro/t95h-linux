# Complete private Actions build

The dispatch workflow builds a single selected profile and emits a matching
`*-install.img`, `*-sysupgrade.bin`, SHA256SUMS, build proof, upgrade test results,
resolved request, package lock, release notes and custom kernel APK/public key.
No hardware writes, reboot, stress test or automatic public release occurs.
Installer download must use the same profile/console as the chosen run.

## Inputs

OpenWrt stable is resolved once from official metadata. The matching ImageBuilder
is downloaded from that release and checked against its official HTTPS SHA256
list. Current code requires the APK-era sunxi/cortexa53 ImageBuilder; incompatible
future releases fail instead of silently using an older release. Kernel sources
are freshly downloaded with the repository archive hash and patched in order.

`boards/t95h/build-inputs.json` pins a private release asset containing only the
existing compiler toolchain, tested 4 MiB boot prefix and allowlisted firmware.
Every firmware file is checked against the profile lock. The old regulatory
files embedded in the pinned kernel are separate from the current OpenWrt
wireless-regdb package. No personal SD image, host key, shadow file or signing
private key is included. The prefix contains the tested partition table and
SPL/BL31/U-Boot chain; it is not rebuilt or experimentally replaced by CI.

This provides an independent private runner build, not yet a public
source-complete distribution. A standalone boot-chain source recipe and complete
redistribution license/provenance inventory remain required before that claim.

## Signing

Repository secret `T95H_APK_SIGNING_KEY` holds a dedicated persistent build key.
The runner writes it only to RUNNER_TEMP with restrictive permissions and removes
it in an always step. Only its public key and the signed custom kernel APK are
artifacts. Official package verification keys come from the matching ImageBuilder.
Package revisions use 1000 + GITHUB_RUN_NUMBER; this is an APK revision, not a
kernel release candidate. The Linux kernel stays 7.2.3.

Sysupgrade contains the kernel and its matching modules together. Never mix
stock OpenWrt kmods for a different kernel with this image. A hosted repository
for individual custom-kmod APK updates is a separate feature and is not implied
by providing the complete sysupgrade artifact. The packaged custom kernel APK
currently owns the selected modules together.

## Verification and limitations

Source/profile/firmware checks, module vermagic, signed APK verification,
filesystem checks, complete direct image readbacks and simulated upgrade tests
are performed. Install and upgrade are derived from the same payload. Hardware
limitations are included in RELEASE-NOTES.md; tests do not imply a stability
certification. Build logs are saved on workflow failure without private keys.

No second comparison build is performed. A fresh job re-resolves package feeds;
package-lock.json records the actual installed versions. Exact long-term replay
of moving upstream package feeds requires an archived package mirror in addition
to the recorded manifests.
