#!/bin/bash
set -euxo pipefail


VENV_PATH="$(dirname $BASH_SOURCE)/../mnt/dietpi_userdata/qudio"

python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"


PIP_PACKAGES="tekore luma.emulator luma.oled watchdog evdev"
if [[ $(pip3 show $PIP_PACKAGES 3>&1 2>&3 1>/dev/null) != "" ]]; then
  pip3 install $PIP_PACKAGES
else
    echo "Python Packages are already installed: ${PIP_PACKAGES}"
fi
