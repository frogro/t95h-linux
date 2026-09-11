# udevil source relocation

Run 34593370177 passed strace and failed fetching udevil (GitHub and LibreELEC mirror HTTP 404).
The locked commit f2b715d1d821e4b69b2fb0864a5a178dd67877f0 is available in arnie97/udevil-ng.
Its tree is 7f90f19f8dbd5cf574ab63c39bf0b6cddc326ca8.
All 71 archived files, symlink targets and modes were compared with git archive of that commit and matched.
The new archive SHA256 is 9285649d4304e7aac303d67e9ddcc6979602296bbfd80cf984317701de3a46e9.
The wrapper directory is now udevil-ng-${PKG_VERSION}; PKG_SOURCE_DIR accounts for it.
No package-version or hardware change is made. This verifies source retrieval, not an image build or hardware functionality.
