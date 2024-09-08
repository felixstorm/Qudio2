#!/bin/bash
set -euo pipefail


"$(dirname $BASH_SOURCE)/librespot-auth-x86_64-linux-musl-static/librespot-auth" \
    --name "Qudio2 LibreSpot-Auth Dummy" \
    --path "$(dirname $BASH_SOURCE)/../mnt/dietpi_userdata/qudio/librespot_credentials.json"
