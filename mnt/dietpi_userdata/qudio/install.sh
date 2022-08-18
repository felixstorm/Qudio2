#!/bin/bash
set -euo pipefail


echo "*** $(realpath $BASH_SOURCE) Starting on $(hostname -A) ($(hostname -I))"

# when called by SSH, PATH is not correct
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH

pushd /mnt/dietpi_userdata/qudio >/dev/null
echo "PWD: ${PWD}"


# remove older and/or unnecessary services & files (just in case)
if [[ -e /etc/systemd/system/qudio-control.service || -e /etc/systemd/system/qudio-display.service ]]; then
  systemctl stop qudio-control.service qudio-display.service || true
  rm -f /etc/systemd/system/qudio-control.service /etc/systemd/system/qudio-display.service
fi
if [ -e /etc/systemd/system/spotifyd.service ]; then
  systemctl stop spotifyd.service
  rm -f /etc/systemd/system/spotifyd.service
  rm -rf /etc/systemd/system/spotifyd.service.d
fi
if [ -e /etc/systemd/system/librespot.service ]; then
  systemctl stop librespot.service
  rm -f /etc/systemd/system/librespot.service
fi
rm -f /var/www/index.nginx-debian.html


# librespot needs a user (with shell for the hook)
id -u qudio &>/dev/null || sudo useradd qudio
sudo usermod --home /mnt/dietpi_userdata/qudio --shell /bin/bash qudio
sudo usermod -a -G audio,gpio,video,i2c,input qudio


# fix permissions just in case they're messed up
chown qudio:root -R .
chmod u+rw,g+r-w,o+r-w -R .
chmod u+rw,g+r-w,o+r-w \
    /etc/asound.conf \
    /etc/rc_keymaps/jbl_onstage_iii.toml \
    /etc/systemd/system/qudio.service /etc/systemd/system/librespot-java.service

# fix audio on Raspberry Pi 3 QA system only
if [[ $(aplay -L) =~ "bcm2835" ]]; then
  sed -i 's/"dmix"/"hw:0,0"/g' /etc/asound.conf
fi


# RO file system: create links to /run and /tmp for folders that are expected to be writable in any case
rm -rf /var/lib/dhcp; ln -s /run /var/lib/dhcp
rm -rf /var/tmp/dietpi/logs; ln -s /tmp /var/tmp/dietpi/logs


# apt packages
APT_PACKAGES="fswebcam zbar-tools libopenjp2-7 ir-keytable" # libopenjp2-7 is for luma.oled
if ! dpkg -s $APT_PACKAGES >/dev/null 2>&1; then
    apt install -y $APT_PACKAGES
else
    echo "Packages are already installed: ${APT_PACKAGES}"
fi


# stock JBL infrared remote control support
if ! grep -q 'dtoverlay=gpio-ir' /boot/config.txt ; then
  echo -e "\n#-------IR-------\ndtoverlay=gpio-ir,gpio_pin=16" >> /boot/config.txt
fi
if ! grep -q 'jbl_onstage_iii' /etc/rc_maps.cfg ; then
  echo -e "\n*       *                        jbl_onstage_iii.toml" >> /etc/rc_maps.cfg
fi


# Python packages and compileall
PIP_PACKAGES="tekore luma.oled watchdog evdev"
if [[ $(pip3 show $PIP_PACKAGES 3>&1 2>&3 1>/dev/null) != "" ]]; then
  pip3 install $PIP_PACKAGES
else
    echo "Python Packages are already installed: ${PIP_PACKAGES}"
fi

$(dirname $BASH_SOURCE)/python_compileall.sh


# refresh services
systemctl daemon-reload
systemctl enable librespot-java.service qudio.service


popd >/dev/null

echo "*** $(realpath $BASH_SOURCE) Completed"
