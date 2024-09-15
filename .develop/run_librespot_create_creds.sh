#!/bin/bash
set -euxo pipefail

GLS_CREDS_JSON="$(dirname "$BASH_SOURCE")/go-librespot-credentials${1:+-$1}.json"

"$(dirname "$BASH_SOURCE")/go-librespot-x86_64" \
    -config_path "$(dirname "$BASH_SOURCE")/go-librespot-config-create-creds.yml" \
    -credentials_path "$GLS_CREDS_JSON"
