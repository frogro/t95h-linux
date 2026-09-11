# Accept only the complete, validated binding; never unload a live GPU.
if [ "$(basename "$(readlink -f "$G/driver")")" = panfrost ] &&
   [ "$(readlink -f /sys/class/drm/renderD128/device)" = "$(readlink -f "$G")" ] &&
   [ "$(basename "$(readlink -f "$P/driver")")" = t95h-ana-provider-test ]; then
    echo panfrost > "$G/driver_override"
    echo 'T95H: existing Panfrost/provider bindings verified; no duplicate insertion'
    exit 0
fi
