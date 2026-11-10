#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "$(realpath -- "$0")")/../.."

if [[ "$(dpkg-query -W -f='${Status}' conky-all 2>/dev/null || true)" != "install ok installed" ]]; then
    sudo apt-get update
    sudo apt-get install -y conky-all
fi

if [[ ! -f "$HOME/.config/conky/conky.conf" ]] || ! cmp -s setup/conky/conky.conf "$HOME/.config/conky/conky.conf"; then
    install -D -m 0644 setup/conky/conky.conf "$HOME/.config/conky/conky.conf"
    echo "Installed Conky monitor configuration."
fi
if [[ ! -f "$HOME/.config/autostart/conky.desktop" ]] || ! cmp -s setup/conky/conky.desktop "$HOME/.config/autostart/conky.desktop"; then
    install -D -m 0644 setup/conky/conky.desktop "$HOME/.config/autostart/conky.desktop"
    echo "Enabled Conky at graphical login."
fi
