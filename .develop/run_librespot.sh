#!/bin/bash
set -euxo pipefail

QUDIO_INI="$(realpath $(dirname $BASH_SOURCE))/qudio_${1:-testdev}.ini"
SPOTIFY_DEVICE_NAME=$(awk -F "=" '/SPOTIFY_DEVICE_NAME/ {print $2}' "$QUDIO_INI")

LIBRESPOT_CACHE="$(realpath $(dirname $BASH_SOURCE))/.librespot_cache"
mkdir -p "$LIBRESPOT_CACHE"
cp "$(dirname $BASH_SOURCE)/librespot_credentials_${1:-testdev}.json" "$LIBRESPOT_CACHE/credentials.json"

pushd $(dirname $BASH_SOURCE)

./librespot_x86-64 \
    --name "$SPOTIFY_DEVICE_NAME" \
    --cache "$LIBRESPOT_CACHE" \
    --onevent "$PWD/../mnt/dietpi_userdata/qudio/librespot_hook.sh" \
    --initial-volume 70

popd
