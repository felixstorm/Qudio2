# QR-Code based Spotify Player for Children

- Hardware based on http://www.tilman.de/projekte/qudio/ with the following changes
  - use Raspberry Pi Camera instead of USB camera
    - RPi Camera focus must be changed for the rather short operating distance by cutting the glue and turning the lens. This can be a rather ugly procedure and there is no real guarantee for success.
    - Useful link: https://projects.raspberrypi.org/en/projects/infrared-bird-box/6
  - add an 1.3" OLED display (SH1106 type)
  - add external USB port for future enhancements (like playing CDs, use USB media etc.)
  - onshape Link of the adapted case: https://cad.onshape.com/documents/0a8bb1d542788dc36d74f979/w/71ac1db00973e66dbf9d59d4/e/7399a80cda5698887abc2b3d?renderMode=0&uiState=617e9dee49988a5627247be8

- Software
  - Originally the software had been based on Volumio (https://volumio.com) and did generally work, but startup time was rather slow and response to commands as well (kids seem to get rather demanding these days ;-) )
  - Therefore I switched away from Volumio to using DietPi (which I am also using for my home linux server) and `spotifyd` (https://github.com/Spotifyd/spotifyd).
  - Now the startup time and general responsiveness have improved greatly. There is no web interface anymore, but that is fine for me (although I might add a web based "kill switch" at some time in the future ;-) )

  !!!!! TBD !!!!!

  - Problems with spotifyd, dbus not working on RPi Zero, potentially move to vollibrespot


## Installation

- DietPi (image)
  - Get DietPi Raspberry Pi image from https://dietpi.com/
  - Burn image with `rufus` or similar
  - Before first start copy `/boot` to SD card and adjust
    - Hostname (`AUTO_SETUP_NET_HOSTNAME`)
    - potentially also lines containing `QTEST`

- Wait for DietPi First Run Setup to complete.
  - Potentially helpful commands:
    ```
    tail -fn10000 /var/tmp/dietpi/logs/dietpi-update.log
    tail -fn10000 /var/tmp/dietpi/logs/dietpi-firstrun-setup.log
    htop # if unsure, use htop to check what is really happening
    ```

- Manual Steps
  ```
  # openssh-sftp-server allows to use WinSCP / SSHFS even with Dropbear
  apt install -y openssh-sftp-server

  # add your SSH key (but should probably also work without it if you do not change the DietPi default password)
  cd ~; mkdir .ssh; touch .ssh/authorized_keys; chmod 0700 ~/.ssh -R; chown root:root ~/.ssh -R; nano .ssh/
  authorized_keys
  ssh-rsa xxxxx yy:yy:yy:yy:... rsa-key-name
  ```

- Run `dietpi-config` to adjust settings:
  - Display
    ○ RPi Camera: on (GPU Mem will be set automatically)
    ○ Rpi Camera LED: off
  - Advanced:
    ○ I2C: 400 kHz, on
  - No need to reboot - it will come later anyway.

- Copy additional files
  - Only works from Windows for now!
  - Need to have SSHFS for Windows (https://github.com/billziss-gh/sshfs-win) installed and `plink.exe` (from Putty) installed and accessible in PATH
  - From your Windows box, run `push_to_device.cmd 192.168.x.y` to copy files to Raspberry Pi Zero and to run `install.sh` script.
  - Reboot RPi to see if everything works (connect with SSH/Putty): `systemctl reboot`
  - After restart run `journalctl -n10000` and check logs for errors (some minor errors are expected)

- Change `fstab` and change `/` and `/boot` mounts to `ro`: `nano /etc/fstab`
  - Reboot RPi again to see if everything works: `systemctl reboot`
  - After restart run `journalctl -n10000` again and check logs
