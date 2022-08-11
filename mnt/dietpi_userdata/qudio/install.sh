#!/bin/bash
set -euo pipefail


echo "*** $(realpath $BASH_SOURCE) Starting on $(hostname -A) ($(hostname -I))"

# when called by plink, PATH is not correct
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH

pushd /mnt/dietpi_userdata/qudio >/dev/null
echo "PWD: ${PWD}"


# copying using SSHFS might mess up permissions
chown qudio:root -R .
chmod u+rw,g+r-w,o+r-w -R .
chmod u+rw,g+r-w,o+r-w \
    /etc/asound.conf \
    /etc/rc_keymaps/jbl_onstage_iii.toml \
    /etc/systemd/system/qudio-*.service /etc/systemd/system/librespot.service

# Raspberry Pi 3 QA system only
if [[ $(aplay -L) =~ "bcm2835" ]]; then
  sed -i 's/"dmix"/"hw:0,0"/g' /etc/asound.conf
fi


# cannot use subfolders as they would need to be created on every boot
rm -rf /var/lib/dhcp; ln -s /run /var/lib/dhcp
rm -rf /var/tmp/dietpi/logs; ln -s /tmp /var/tmp/dietpi/logs

# disable crda udev rule as it seems to fail with ro file system and crashes the whole network-online target, i.e. target gets reached before an IP address has been acquired
# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=871643
rm -rf /etc/udev/rules.d/85-regulatory.rules; ln -s /dev/null /etc/udev/rules.d/85-regulatory.rules

if ! grep -q 'dtoverlay=gpio-ir' /boot/config.txt ; then
  echo -e "\n#-------IR-------\ndtoverlay=gpio-ir,gpio_pin=16" >> /boot/config.txt
fi
if ! grep -q 'jbl_onstage_iii' /etc/rc_maps.cfg ; then
  echo -e "\n*       *                        jbl_onstage_iii.toml" >> /etc/rc_maps.cfg
fi


DEB_PACKAGES="fswebcam zbar-tools libopenjp2-7 ir-keytable" # libopenjp2-7 is for luma.oled
if ! dpkg -s $DEB_PACKAGES >/dev/null 2>&1; then
    apt install -y $DEB_PACKAGES
else
    echo "Packages are already installed: ${DEB_PACKAGES}"
fi


PIP_PACKAGES="tekore luma.oled watchdog evdev"
if [[ $(pip3 show $PIP_PACKAGES 3>&1 2>&3 1>/dev/null) != "" ]]; then
  pip3 install $PIP_PACKAGES
else
    echo "Python Packages are already installed: ${PIP_PACKAGES}"
fi

$(dirname $BASH_SOURCE)/python_compileall.sh


# librespot needs a user (with shell for the hook)
id -u qudio &>/dev/null || sudo useradd qudio
sudo usermod --home /mnt/dietpi_userdata/qudio --shell /bin/bash qudio
sudo usermod -a -G audio,gpio,video,i2c,input qudio


if [ -e /etc/systemd/system/spotifyd.service ]; then
  # disabling does not survive reboots (for whatever reason) and masking is not possible for unit files in /etc/systemd/system
  systemctl stop spotifyd.service
  mv -f /etc/systemd/system/spotifyd.service spotifyd.service.disabled
fi
systemctl daemon-reload
systemctl enable librespot.service
systemctl enable qudio-display.service
systemctl enable qudio-control.service


popd >/dev/null

echo "*** $(realpath $BASH_SOURCE) Completed"
