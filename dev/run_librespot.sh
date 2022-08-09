#!/bin/bash
set -euxo pipefail

pushd $(dirname $BASH_SOURCE)

SPOTIFY_DEVICE_NAME=$(awk -F "=" '/SPOTIFY_DEVICE_NAME/ {print $2}' qudio_test.ini)
SPOTIFY_USERNAME=$(awk -F "=" '/SPOTIFY_USERNAME/ {print $2}' qudio_test.ini)
SPOTIFY_PASSWORD=$(awk -F "=" '/SPOTIFY_PASSWORD/ {print $2}' qudio_test.ini)

./librespot_x86-64 \
    --name ${SPOTIFY_DEVICE_NAME} \
    --username ${SPOTIFY_USERNAME} \
    --password ${SPOTIFY_PASSWORD} \
    --onevent $PWD/../mnt/dietpi_userdata/qudio/librespot_hook.sh \
    --initial-volume 30

popd
