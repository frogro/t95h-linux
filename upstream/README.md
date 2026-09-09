# Upstream preparation — local assessment, not a submitted patch series

Evidence: outputs/live-console-check/20260907T171658Z in the enclosing project.
The boot with the private PPU compatible removed the upstream ANA -22 probe and
TM16xx -ENXIO errors. Early ModemManager D-Bus connection errors are absent.
Panfrost now reports early deferred-probe timeout -110, then binds successfully
at 135 seconds with renderD128. AP is active. ext4 unchecked warning persists.
Do not describe this as an entirely error-free boot or an upstream-ready PPU fix.

| Change | Intended upstream | Remaining work |
| --- | --- | --- |
| Analog/AHUB clock ownership and BCLK fixes | Linux ASoC / pending AHUB series | Isolate each fix, establish exact dependency tree and original authorship, review clock release/error paths; no acoustic validation claimed |
| T95H DT wiring / regulator support | Linux sunxi / regulator | Proper bindings and reusable hardware driver instead of experiment-specific inherited-state policy |
| PPU ANA EL3 confirmation | Linux pmdomain plus TF-A | Document secure/nonsecure register visibility; replace private SMC ABI with an agreed firmware interface; resolve early probe ordering; no invented hardware compatible as upstream solution |
| FD655 userspace implementation | Separate userspace project or later Linux LED/display driver | Hardware protocol/binding and subsystem review; disabling failed child node is local DT integration only |
| ModemManager cached-event guard | OpenWrt packages | Rebase against current package source; preserve add/remove/cache replay semantics; submit independently of kernel |
| Late WLAN/GPU scripts, console choice, sysupgrade | T95H/OpenWrt integration | Not Linux kernel patches |
| Existing PWM/Cedrus/PHY/DRM series | Original authors' series | Preserve attribution, identify only our incremental changes; never resubmit their work as ours |

Next submission preparation: reproduce each minimal issue on the relevant
maintainer tree, one logical fix per patch, dependency notes, build/checkpatch
and relevant test evidence. Keep local kernel 7.2.3 and boot-chain locks unchanged
while doing upstream rebases in a separate tree. No messages or patches sent.
Reference: https://docs.kernel.org/process/submitting-patches.html
