# XR819 interface publication race (2026-09-09)

Two photographed panics, with and without the SPL SD retry experiment, show
`wsm_get_tx+0xf4/0x75c` calling the spinlock slowpath during AP creation.
The shipped Actions kernel SHA256 is
`a58e1c981e2362ef6d711de06130775485e1baa690d536731d59b90a03970da5`.
Its 0x75c-byte wsm_get_tx body at Image offset 0x704884 is byte-identical to the
local symbolized binary: the call at +0xf0 takes priv->vif_lock; +0xf4 is its
return address.

mac80211 allocates sizeof(struct xradio_vif) as inline drv_priv. The conversion
helper returns this inline structure, whose first members are enabled and
vif_lock. xradio_add_interface nevertheless stored a pointer into drv_priv,
corrupting those first eight bytes on ARM64. It then published vif_list before
xradio_vif_setup initialized vif_lock. A concurrent BH could therefore acquire
the corrupted lock. A late start can change this race's probability, not fix it.

The follow-up patch removes the obsolete pointer store, initializes vif_lock
before publication, and removes its later reinitialization. The earlier 32-bit
register-read correction remains first in the incremental patch order.

The patch replay/order test passes against locked original sources. A separate
local C reproducer confirms the ARM64 overwrite. Test kernel compilation passes
and Module.symvers remains unchanged. Hardware validation is pending; missed
interrupt recovery and SDIO data errors are separate unresolved issues.
