#!/bin/bash
set -euo pipefail


if (( $# < 1 )); then
    echo "ERROR: Missing target"
    exit 1
fi

target=$1
ssh_target="root@$1"
shift


set -x

ssh $ssh_target 'mount -o remount,rw /'

# /boot has already been copied manually before
rsync_includes=('/etc/***' '/mnt/***' '/opt/***')
rsync_excludes=('*/__pycache__/' '*/qudio.ini')
rsync -avh \
    "${rsync_excludes[@]/#/--exclude=}" \
    "${rsync_includes[@]/#/--include=}" \
    --exclude='*' \
    "$(dirname $BASH_SOURCE)/.." "$ssh_target:/"

ssh $ssh_target '/mnt/dietpi_userdata/qudio/install.sh'

if [ "$target" != "192.168.0.142" ]; then
    ssh $ssh_target 'mount -o remount,ro /'
fi

if echo $* | grep -E --invert-match "(^|\s)(-n|--no-restart)($|\s)" -q; then
    ssh $ssh_target 'systemctl restart librespot.service; systemctl start qudio-control.service qudio-display.service'
fi
