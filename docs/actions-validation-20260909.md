# End-to-end Actions validation — 2026-09-09

Successful run: https://github.com/frogro/t95h-linux/actions/runs/34363631215
Build source commit: `5f72d92`. Profile `base-A-B`, console `dual`.
OpenWrt resolved to 25.12.5; Linux remained 7.2.3-t95h-candidate3.

The clean runner downloaded the locked build dependencies and kernel archive,
replayed the consolidated patch and four incremental xradio u32 read corrections,
compiled the kernel and 35 matching modules, signed the custom kernel APK,
installed 252 packages into a fresh root, prepared runtime services and generated
both installation and sysupgrade images. Image readbacks and all twelve upgrade
software checks passed. The artifact upload completed successfully.

The ThinkPad installer then downloaded the artifact and verified SHA256SUMS.
The custom kernel APK hash and signature were checked with the downloaded public
key. Extracting boot.scm from the downloaded FAT image confirmed the exact
live-tested SD-retry payload, SHA256:
`4dfd35ab3766382560594c4a5a6fa50c439a3859505f9091b17b21c56b64b03f`.

- Install SHA256: `52bf8dea4e5b92b2a48c0816292a713d5828bd8d77dff3b651a9c7a25d1e7482`
- Sysupgrade SHA256: `4102fd46794046da6685c676ae4a845e3e6e5fa03298dc09b78097b0bf410398`
- Kernel APK revision: `7.2.3-r1002` (package revision, not another Linux version).

First attempt 34363320984 stopped before compilation because the config guard
mistook two auto-detected host-tool capabilities for requested target features.
The exact OPENSSL_SUPPORTS_ML_DSA and PAHOLE_HAS_LANG_EXCLUDE probes are now
recorded separately; all requested target drivers/features remain enforced.

This validates the private end-to-end software build and download path for this
profile. Other selectable profiles have source/config checks but were not newly
compiled in this validation run. No device was flashed or rebooted, and no new
hardware, audio-listening or stress test was performed. The documented WLAN,
coldboot, GPU and audio hardware limitations remain. Public source-complete
redistribution still requires the documented binary-input provenance/license work.

## GPU startup follow-up

The first upgraded boot exposed an OpenWrt shell compatibility issue:
`IPKG_INSTROOT: parameter not set` while sourcing `/lib/functions.sh` under
`set -u`. This stopped the late GPU worker before provider registration.
The runtime now evaluates the radio policy in a subshell with nounset disabled;
the parent worker retains strict checks. The regression test includes an unset
OpenWrt helper variable. The 15 consecutive readiness samples now overlap the
120-second minimum uptime instead of following it. The minimum uptime and all
network, regulator and driver checks remain enforced. This changes only the
runtime script, not the kernel or power settings.
