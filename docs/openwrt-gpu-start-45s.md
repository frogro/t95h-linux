# OpenWrt: earlier guarded GPU start

Profiles B and A+B now require at least 45 seconds uptime instead of 120.
The existing 15 consecutive readiness samples are unchanged, including LAN,
SSH, completed WLAN worker, configured radio, regulator state and voltage checks.
The base WLAN worker already loads the regulator after LAN/SSH readiness; it
has no fixed 60-second startup delay and is unchanged.

AnotterKiosk completed three 30/45-second starts, including a cold boot after
two power-on attempts. That supports testing this timing but does not validate
OpenWrt WLAN/GPU interaction. The new OpenWrt release requires a hardware test.
This change does not claim to remove early deferred-probe -110 warnings or
fix boot reliability. Kernel, SPL, GPU clocks and supply voltages are unchanged.
Reverting the minimum uptime and its log message to 120 restores prior timing.
