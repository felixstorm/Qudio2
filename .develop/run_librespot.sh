#!/bin/bash
set -euxo pipefail

DEVICE_ROOT="$(realpath $(dirname $BASH_SOURCE)/..)"

QUDIO_INI="$(dirname $BASH_SOURCE)/qudio_testdev.ini"
SPOTIFY_DEVICE_NAME="$(awk -F "=" '/SPOTIFY_DEVICE_NAME/ {print $2}' $QUDIO_INI)"
SPOTIFY_USERNAME="$(awk -F "=" '/SPOTIFY_USERNAME/ {print $2}' $QUDIO_INI)"
SPOTIFY_PASSWORD="$(awk -F "=" '/SPOTIFY_PASSWORD/ {print $2}' $QUDIO_INI)"

pushd "$DEVICE_ROOT/mnt/dietpi_userdata/qudio"

java -jar $DEVICE_ROOT/opt/librespot-java/librespot-api-1.6.2.jar \
    --conf-file=$DEVICE_ROOT/etc/opt/librespot-java.toml \
    --deviceName=${SPOTIFY_DEVICE_NAME} \
    --auth.username=${SPOTIFY_USERNAME} \
    --auth.password=${SPOTIFY_PASSWORD} \
    --player.initialVolume=20000

popd
