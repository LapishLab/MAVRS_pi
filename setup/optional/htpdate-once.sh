#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "$(realpath -- "$0")")/../.."

if [[ "$(dpkg-query -W -f='${Status}' htpdate 2>/dev/null || true)" != "install ok installed" ]]; then
    sudo apt-get update
    sudo apt-get install -y htpdate
fi

# The server sets Pi time before recordings. Use HTTP time once at boot instead
# of leaving htpdate's daemon or its network if-up hook active continuously.
sudo systemctl disable htpdate.service
sudo systemctl stop htpdate.service
if [[ -f /etc/default/htpdate ]] && ! grep -Eq '^[[:space:]]*HTP_IFUP=no[[:space:]]*$' /etc/default/htpdate; then
    if grep -Eq '^[[:space:]]*#?[[:space:]]*HTP_IFUP=' /etc/default/htpdate; then
        sudo sed -i -E 's/^[[:space:]]*#?[[:space:]]*HTP_IFUP=.*/HTP_IFUP=no/' /etc/default/htpdate
    else
        printf '\nHTP_IFUP=no\n' | sudo tee -a /etc/default/htpdate >/dev/null
    fi
fi

if [[ ! -f /etc/systemd/system/htpdate-once.service ]] || ! cmp -s setup/systemd/htpdate-once.service /etc/systemd/system/htpdate-once.service; then
    sudo install -D -m 0644 setup/systemd/htpdate-once.service /etc/systemd/system/htpdate-once.service
    sudo systemctl daemon-reload
fi
sudo systemctl enable htpdate-once.service
