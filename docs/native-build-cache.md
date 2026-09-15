# Native OpenWrt build checkpoints

The Kernel 6 workflow restores the newest compatible checkpoint before building,
then saves `dl`, `build_dir`, `staging_dir`, and `bin` after a successful or failed
build command. Each run/attempt writes a new immutable cache entry. A failed build
remains failed; rerunning it restores the available intermediate work.

Compatibility includes the pinned OpenWrt commit (and its pinned feeds), profile,
public signing key, native source files/overlays/feed patches, and the preparation
and build functions. Tests, publishing code and final image-package validation
are excluded. These checks still run on every attempt; cache restoration never
replaces package, ABI, image or signature verification. Configuration and signing
keys are prepared freshly and are not restored from the checkpoint.

When adding build-affecting helpers outside the existing preparation/build
functions, include them in `build_fingerprint`. Bump its runner/environment version
when changing runner dependencies or the compatibility contract. Cache v2 does
not restore v1 entries: the first build establishes a new baseline/feed identity.

The build command stops after 330 minutes to leave time within the six-hour job
limit for checkpoint upload and diagnostics. Cache upload is limited to 25 minutes
and is best-effort; a cache service/storage failure does not discard an otherwise
successful image. Manual cancellation and runner loss cannot guarantee a final
checkpoint. Existing running jobs retain their original workflow definition.

No automatic rebuild is dispatched. Use the normal workflow dispatch for the
same profile, or retry a failed run, to continue from a compatible saved cache.
