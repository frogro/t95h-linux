#!/bin/bash
set -eu
cd "$(dirname "$0")/../../build/libreelec"
export PROJECT=T95H ARCH=aarch64 LOGCOMBINE=fail MTIMMEDIATE=no
export CONCURRENCY_MAKE_LEVEL="$(nproc)"
export T95H_BUILD_DEADLINE="$(( $(date +%s) + ${T95H_PHASE_SECONDS:-10800} ))"
export T95H_PAUSE_MARKER="$PWD/../libreelec-paused"
rm -f "$T95H_PAUSE_MARKER"
# The scheduler stops submitting new packages at 180 min, then drains them.
# The outer deadline reserves at least 45 minutes for archiving/upload.
set +e
set -o pipefail
timeout --signal=TERM --kill-after=60s 300m make system 2>&1 | tee ../libreelec-build.log
rc=${PIPESTATUS[0]}
set -e
if [ "$rc" = 0 ]; then
  echo 'state=complete' >> "$GITHUB_OUTPUT"
elif [ -f "$T95H_PAUSE_MARKER" ] && [ "$rc" != 124 ] && [ "$rc" != 137 ]; then
  echo 'state=paused' >> "$GITHUB_OUTPUT"
  echo 'Package boundary reached; continuing in a fresh job.'
else
  # No checkpoint is claimed after timeout or compiler failure.
  echo "Build failed (exit $rc); not publishing a resumable state."
  exit "$rc"
fi
