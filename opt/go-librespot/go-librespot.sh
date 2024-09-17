#!/bin/bash
set -euxo pipefail

QUDIO_DIR="/mnt/dietpi_userdata/qudio"
QUDIO_INI="${QUDIO_INI:-${QUDIO_DIR}/qudio.ini}"
GLS_CREDS_JSON="${GLS_CREDS_JSON:-${QUDIO_DIR}/go-librespot-credentials.json}"
GLS_CONFIG_TMPL="${GLS_CONFIG_TMPL:-${QUDIO_DIR}/go-librespot-config.yml.tmpl}"
GO_LIBRESPOT="${GO_LIBRESPOT:-/opt/go-librespot/go-librespot}"

export SPOTIFY_DEVICE_NAME=$(awk -F "=" '/SPOTIFY_DEVICE_NAME/ {print $2}' "$QUDIO_INI")
export DEVCREDS_USERNAME=$(sed -r -n -e 's/.*"username": *"([^"]*)".*/\1/p' < "$GLS_CREDS_JSON")
envsubst < "$GLS_CONFIG_TMPL" > /tmp/go-librespot-config.yml
if [[ -v GLS_CONFIG_EXTRA ]]; then
    echo "$GLS_CONFIG_EXTRA" >> /tmp/go-librespot-config.yml
fi

"$GO_LIBRESPOT" \
    -config_path /tmp/go-librespot-config.yml \
    -credentials_path "$GLS_CREDS_JSON"
