# QR-Code based Spotify Player for Children


## Disclaimer

Since my time is pretty limited, this is meant just to make a personal project publicly available and I will most likely not be able to react on issues or pull requests or provide any other form of support for it. But feel free to fork again and enhance it yourself.


## Heritage and History

- Hardware based on http://www.tilman.de/projekte/qudio/ with the following changes
  - Use Raspberry Pi Camera instead of USB camera
    - RPi Camera focus must be changed for the rather short operating distance by cutting the glue and turning the lens. This can be a rather ugly procedure and there is no real guarantee for success.
    - Useful link: https://projects.raspberrypi.org/en/projects/infrared-bird-box/6
  - Add an 1.3" OLED display (SH1106 type)
  - ~~Add external USB port for future enhancements (like playing CDs, use USB media etc.)~~ => no software support for it anymore
  - onshape Link of the adapted case: https://cad.onshape.com/documents/0a8bb1d542788dc36d74f979/w/71ac1db00973e66dbf9d59d4/e/7399a80cda5698887abc2b3d?renderMode=0&uiState=617e9dee49988a5627247be8

- Software
  - Originally the software had been based on [Volumio](https://volumio.com) and did generally work, but startup time was rather slow and response to commands as well (kids seem to get rather demanding these days ;-) )
  - Therefore I switched away from Volumio to using DietPi (which I am also using for my home linux server) and [`spotifyd`](https://github.com/Spotifyd/spotifyd) around 2021-10.
  - This has greatly improved the startup time and general responsiveness. There is no web interface anymore, but that is fine for me (although I might add a web based "kill switch" at some time in the future ;-) )
  - Originally I made the decision for `spotifyd` hoping to be able to use it's `dbus` capabilities to be able to control the player using the buttons. Unfortunately it's Pi 1 & Zero build does not support `dbus`, but I still stayed with `spotifyd` but switched to using the Python library `tekore` instead to control it remotely through the Spotifiy Connect service.
  - In 2022-08 an issue came up that some Spotify APs became non-responsive basically breaking this player completely. And although there existed a workaround using some specially crafted entries in `/etc/hosts` (see this [comment](https://github.com/librespot-org/librespot/issues/972#issuecomment-1195907706) for details) I decided to directly switch to [`librespot`](https://github.com/librespot-org/librespot) instead (which `spotifyd` is based on anyway) since the issue had already been fixed in code there only a few days after it had been discovered.
  - `librespot` primarily is a library, but also comes with a small server application that basically has the same functionality of the `spotifyd` builds for the Pi 1 and Zero. The code seems to be well maintained, but there is a (small) downside with it regarding this specific project: `librespot` seems to need more CPU cycles than `spotifyd` (about 25-30% CPU on a Zero instead of 15-25% with `spotifyd`, probably because more recent versions of `librespot` now use float64 internally instead of float32), but that is still ok for me (being just fine with 96kbit only anyway).
  - Another option would be to switch to [Vollibrespot](https://github.com/ashthespy/Vollibrespot) instead. It is also based on `librespot` and already contains some mechanism to get controlled using a pipe from another process and to also send metadata there. But it seems to only be built for the very purpose of being used with Volumio2, so forking the `librespot` server and adding some control mechanism myself might be preferrable in case the current concept should not work or suffice anymore for whatever reason.


## Installation

- DietPi (image)
  - This is all based on DietPi around version 7.7 or 7.8.
  - Get DietPi Raspberry Pi image from https://dietpi.com/
  - Burn image to a USB stick with `rufus` (Windows) or similar
  - Before first start, copy `/boot` directory to SD card and adjust
    - in `dietpi.txt`
      - Hostname (`AUTO_SETUP_NET_HOSTNAME`)
      - potentially also lines containing `QTEST`
    - and copy `dietpi-wifi.txt.sample` to `dietpi-wifi.txt` and add your WiFi credentials

- Wait for DietPi First Run Setup to complete.
  - Potentially helpful commands:
    ```sh
    tail -fn10000 /var/tmp/dietpi/logs/dietpi-update.log
    tail -fn10000 /var/tmp/dietpi/logs/dietpi-firstrun-setup.log
    # if unsure, use htop to check what is really happening
    htop
    ```

- Manual Steps
  ```sh
  # openssh-sftp-server allows to use sftp: / SSHFS even with Dropbear, rsync to copy files
  apt install -y openssh-sftp-server rsync

  # add your SSH key
  # => since DietPi 8.5 it should also be possible to set an authorized SSH key using AUTO_SETUP_SSH_PUBKEY in `/boot/dietpi.txt` before first boot (see above)
  cd ~; mkdir .ssh; touch .ssh/authorized_keys; chmod 0700 ~/.ssh -R; chown root:root ~/.ssh -R; nano .ssh/
  authorized_keys
  # add content like this: ssh-rsa xxxxx yy:yy:yy:yy:... rsa-key-name
  ```

- Run `dietpi-config` to adjust settings:
  - Display
    ○ RPi Camera: on (GPU Mem will be set automatically)
    ○ Rpi Camera LED: off
  - Advanced:
    ○ I2C: 400 kHz, on
  - No need to reboot - it will come later anyway.

- Copy additional files
  - Only works from Linux. If you are on Windows, try using WSL2 instead, but make sure to also `git clone` from within WSL2 to ensure correct executable flags on the files.
  - From your Linux box, run `.develop/push_to_device.sh 192.168.x.y` to copy the files to the Raspberry Pi Zero and to automatically run the script `install.sh` there after copying.
  - Reboot RPi to see if everything works (connect with SSH/Putty): `systemctl reboot`
  - After restart run `journalctl -n10000` and check logs for errors (some minor errors are to be expected)

- Edit `fstab` and change `/` and `/boot` mounts from `rw` to `ro`: `nano /etc/fstab`
  - Reboot RPi again to see if everything still works: `systemctl reboot`
  - After restart run `journalctl -n10000` again and check logs


## Update DietPi, APT packages and Python packages later
Connect to device using SSH (or Putty), then enter the following commands:  
```bash
# First remount both root and boot file systems read-write
mount -o rw,remount /; mount -o rw,remount /boot
# Then run `dietpi-update` to upgrade DietPi and APT packages
dietpi-update
# Upgrade Python `pip` to latest version
/usr/bin/python3 -m pip install --upgrade pip
# Show outdated Python packages
pip list --outdated
# Upgrade outdated Python packages
pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1  | xargs -n1 pip install -U
# Now reboot
systemctl reboot
```
After the final reboot, the updates should have all been applied and the filesystem should automatically be mounted read-only again.
