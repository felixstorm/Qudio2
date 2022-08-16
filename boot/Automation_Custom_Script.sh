#!/bin/bash

# openssh-sftp-server allows to use sftp: / SSHFS even with Dropbear, rsync to copy files
apt-get install -y openssh-sftp-server rsync

# Camera
/boot/dietpi/func/dietpi-set_hardware rpi-camera enable
{
    # Import DietPi-Globals
    . /boot/dietpi/func/dietpi-globals
    G_CONFIG_INJECT 'disable_camera_led=' "disable_camera_led=1" /boot/config.txt
}

# I2C (Display)
/boot/dietpi/func/dietpi-set_hardware i2c enable
/boot/dietpi/func/dietpi-set_hardware i2c 400
