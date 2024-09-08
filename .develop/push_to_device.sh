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
rsync_includes=('/etc/***' '/mnt/***' '/opt/***' '/var/***')
rsync_excludes=(
    '*/__pycache__/'
    '/mnt/dietpi_userdata/qudio/pyvenv.cfg'
    '/mnt/dietpi_userdata/qudio/bin'
    '/mnt/dietpi_userdata/qudio/include'
    '/mnt/dietpi_userdata/qudio/lib'
    '/mnt/dietpi_userdata/qudio/lib64'
)
# -a would mess up permissions and ownership
rsync -rlt -vh \
    "${rsync_excludes[@]/#/--exclude=}" \
    "${rsync_includes[@]/#/--include=}" \
    --exclude='*' \
    "$(dirname $BASH_SOURCE)/.." "$ssh_target:/"

ssh $ssh_target '/mnt/dietpi_userdata/qudio/install.sh'

if [ "$target" != "192.168.0.142" ]; then
    # remount both / and /boot to completely cleanup
    ssh $ssh_target 'mount -o remount,ro / ; mount -o remount,ro /boot'
fi

if echo $* | grep -E --invert-match "(^|\s)(-n|--no-restart)($|\s)" -q; then
    ssh $ssh_target 'systemctl stop librespot.service qudio.service; systemctl start qudio.service'
fi
