#!/bin/bash
set -euxo pipefail

export QUDIO_INI="$(realpath $(dirname $BASH_SOURCE))/qudio_testdev.ini" 

pushd "$(dirname $BASH_SOURCE)/../mnt/dietpi_userdata/qudio"

LOGLEVEL=DEBUG ./qudio.py

popd
