#!/bin/bash
set -euxo pipefail

export QUDIO_INI="$(realpath $(dirname $BASH_SOURCE))/qudio_test.ini" 

pushd "$(dirname $BASH_SOURCE)/../mnt/dietpi_userdata/qudio"
./qudio-display.py
popd
