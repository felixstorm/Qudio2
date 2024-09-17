#!/bin/bash
set -euxo pipefail

THIS_DIR="$(realpath $(dirname "$BASH_SOURCE"))"
QUDIO_DIR="${THIS_DIR}/../mnt/dietpi_userdata/qudio"

export QUDIO_INI="${THIS_DIR}/qudio-${1:-testdev}.ini"
export GLS_CREDS_JSON="${THIS_DIR}/go-librespot-credentials-${1:-testdev}.json"
export GLS_CONFIG_TMPL="${QUDIO_DIR}/go-librespot-config.yml.tmpl"
export GO_LIBRESPOT="${THIS_DIR}/go-librespot-x86_64"
export GLS_CONFIG_EXTRA="log_level: debug"

"${THIS_DIR}/../opt/go-librespot/go-librespot.sh"
