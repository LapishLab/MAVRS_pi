#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "$(realpath -- "$0")")/../.."

# PipeWire loads /etc drop-ins after its packaged /usr/share configuration.
if [[ -f /usr/share/pipewire/pipewire.conf ]]; then
    target=/etc/pipewire/pipewire.conf.d/90-mavrs-clock.conf
    if [[ ! -f "$target" ]] || ! cmp -s setup/pipewire/90-mavrs-clock.conf "$target"; then
        sudo install -D -m 0644 setup/pipewire/90-mavrs-clock.conf "$target"
        echo "Configured PipeWire sample rates (takes effect when PipeWire restarts)."
    fi
fi
