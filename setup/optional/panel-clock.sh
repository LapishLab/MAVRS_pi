#!/usr/bin/env bash
set -euo pipefail

# Bookworm uses the flat path; newer wf-panel-pi uses a nested config directory.
if [[ -f "$HOME/.config/wf-panel-pi/wf-panel-pi.ini" || -f /etc/xdg/wf-panel-pi/wf-panel-pi.ini ]]; then
    panel_config="$HOME/.config/wf-panel-pi/wf-panel-pi.ini"
else
    panel_config="$HOME/.config/wf-panel-pi.ini"
fi

# Update only clock_format in [panel], preserving all other settings.
panel_tmp=$(mktemp)
trap 'rm -f "$panel_tmp"' EXIT
if [[ -f "$panel_config" ]]; then
    awk '
        function add_clock() {
            if (in_panel && !clock_set) print "clock_format=%y-%m-%d %H:%M:%S"
        }
        /^\[[^]]+\]/ {
            add_clock()
            in_panel = ($0 ~ /^\[panel\][[:space:]]*$/)
            if (in_panel) found_panel = 1
            clock_set = 0
        }
        in_panel && /^[[:space:]]*clock_format[[:space:]]*=/ {
            if (!clock_set) print "clock_format=%y-%m-%d %H:%M:%S"
            clock_set = 1
            next
        }
        { print }
        END {
            add_clock()
            if (!found_panel) {
                print "[panel]"
                print "clock_format=%y-%m-%d %H:%M:%S"
            }
        }
    ' "$panel_config" > "$panel_tmp"
else
    printf '[panel]\nclock_format=%%y-%%m-%%d %%H:%%M:%%S\n' > "$panel_tmp"
fi
if [[ ! -f "$panel_config" ]] || ! cmp -s "$panel_tmp" "$panel_config"; then
    install -D -m 0644 "$panel_tmp" "$panel_config"
    echo "Configured panel clock with seconds in $panel_config (takes effect after panel restart)."
fi
