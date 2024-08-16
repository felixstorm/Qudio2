#!/bin/bash
set -euxo pipefail

export QUDIO_INI="$(realpath $(dirname $BASH_SOURCE))/qudio_${1:-testdev}.ini"

VENV_PATH="$(dirname $BASH_SOURCE)/../mnt/dietpi_userdata/qudio"
source "$VENV_PATH/bin/activate"

pushd "$VENV_PATH"
LOGLEVEL=DEBUG ./qudio.py
popd
