#!/bin/bash

# when called by plink, PATH is not correct
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH

pushd /mnt/dietpi_userdata/spotifyd >/dev/null
echo "PWD: ${PWD}"

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

# spotifyd hook needs a shell
usermod --shell /bin/bash spotifyd
usermod -a -G gpio,video,i2c,input spotifyd

# copying using SSHFS will mess up permissions
chown -R spotifyd:root .
chmod -R 644 .
find -type d -exec chmod +x {} \;
chmod +x *.py *.sh

if test -f spotifyd_creds.sh; then
  . spotifyd_creds.sh
  echo "Using device '${SPOTCONF_DEVICE_NAME}' and user '${SPOTCONF_USERNAME}' for spotifyd."
  sed -i "s/^username\s*=\s*\"[^\"]*\"/username = \"${SPOTCONF_USERNAME}\"/g" spotifyd.conf
  sed -i "s/^password\s*=\s*\"[^\"]*\"/password = \"${SPOTCONF_PASSWORD}\"/g" spotifyd.conf
  sed -i "s/^device_name\s*=\s*\"[^\"]*\"/device_name = \"${SPOTCONF_DEVICE_NAME}\"/g" spotifyd.conf
  sed -i "s/^SPOTIFY_USER_REFRESH\s*=\s*\"[^\"]*\"/SPOTIFY_USER_REFRESH = \"${SPOTCONF_SPOTIFY_USER_REFRESH}\"/g" spotifyd.conf
fi

chmod 644 /etc/asound.conf /etc/systemd/system/qudio-*.service /etc/systemd/system/spotifyd.service.d/override.conf /etc/rc_keymaps/jbl_onstage_iii.toml

if [[ $(aplay -L) =~ "bcm2835" ]]; then
  sed -i 's/"dmix"/"hw:0,0"/g' /etc/asound.conf
fi

systemctl daemon-reload
systemctl enable qudio-display.service
systemctl enable qudio-control.service

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

popd >/dev/null
