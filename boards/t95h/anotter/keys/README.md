# Debian 13 archive public keys

Downloaded from https://ftp-master.debian.org/keys.html on 2026-09-11.
These are public signing keys, not secrets. Primary fingerprints are checked by
the build. Explicit mmdebstrap keyring avoids Ubuntu 24.04's older Debian keyring.
The target installs debian-archive-keyring through the authenticated repository.
APT signature checking remains enabled.
