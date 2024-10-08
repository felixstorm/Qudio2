# QR-Code based Spotify Player for Children


## First of All: Big Thanks to Tilman Liero for His Work: http://www.tilman.de/projekte/qudio/

Without his work on the hardware as well as on the software I would never have started myself on implementing it for my kids! And my kids do love it ;-)


## Personal Disclaimer

Since my time is pretty limited, this is meant primarily to make a personal project publicly available. I will most likely not be able to react on issues asking for changes or pull requests, although I will try to answer questions about the project if I can. But feel free to fork again and enhance it yourself!


## Heritage and History

- Hardware based on http://www.tilman.de/projekte/qudio/ with the following changes
  - Use Raspberry Pi Camera instead of USB camera
    - RPi Camera focus must be changed for the rather short operating distance by cutting the glue and turning the lens. This can be a rather ugly procedure and there is no real guarantee for success.
    - Useful link: https://projects.raspberrypi.org/en/projects/infrared-bird-box/6
  - Add an 1.3" OLED display (SH1106 type)
  - ~~Add external USB port for future enhancements (like playing CDs, use USB media etc.)~~ => no software support for it anymore
  - onshape Link of the adapted case: https://cad.onshape.com/documents/0a8bb1d542788dc36d74f979/w/71ac1db00973e66dbf9d59d4/e/7399a80cda5698887abc2b3d?renderMode=0&uiState=617e9dee49988a5627247be8
  - Instead of using an Apple Dock adapter to feed audio to the JBL and to pull power from it, I decided to solder wires directly to the PCB inside the JBL. I also take 12 volts from the JBL PCB and use a simple step-down buck converter to get 5 volts from it for the Pi Zero. This rules out the adapter as an additional source for power and audio problems and still keeps the JBL main power switch working as before. The player might even work using batteries inside the JBL battery compartment, but I did never try this myself.  
  There seem to exist a few different types of PCB layouts for the JBL On Stage III (P). I came across these two:
    - Type III with mini USB and audio out connectors: [PCB overview](.media/JBL_Type_III_Overview.jpg), [my audio connection details](.media/JBL_Type_III_AudioConnection.jpg), [my power connection details](.media/JBL_Type_III_PowerConnection.jpg)
    - Type IIIP (neither mini USB nor audio out): [PCB overview](.media/JBL_Type_IIIP_Overview.jpg), [my audio connection details](.media/JBL_Type_IIIP_AudioConnection.jpg), [my power connection details](.media/JBL_Type_IIIP_PowerConnection.jpg)
  - I also feed the received IR signal from the JBL to the Pi Zero and decode it there to be able to use the stock JBL IR remote control to not only control volume but also play/pause and next/previous track. Unfortunately I am currently unable to find any photo documenting from where exactly on the JBL PCB I took the IR signal. In case I should find a photo I will add it here.

- Software
  - Originally the software had been based on [Volumio](https://volumio.com) and did generally work, but startup time was rather slow and response to commands as well (kids seem to get rather demanding these days ;-) )
  - Therefore I switched away from Volumio to using DietPi (which I am also using for my home linux server) and [Spotifyd](https://github.com/Spotifyd/spotifyd) around 2021-10.
  - This has greatly improved the startup time and general responsiveness. There is no web interface anymore, but that is fine for me (although I might add a web based "kill switch" at some time in the future ;-) )
  - Originally I made the decision for Spotifyd hoping to be able to use it's [D-Bus](https://en.wikipedia.org/wiki/D-Bus) capabilities to be able to control the player using the buttons. Unfortunately it's Pi 1 & Zero build does [not support D-Bus](https://github.com/Spotifyd/spotifyd/blob/993336f74ec89cb6cad23dd009251e70548761b6/.github/workflows/cd.yml#L72), but I still stayed with Spotifyd but switched to using the Python library [Tekore](https://github.com/felix-hilden/tekore) instead to control it remotely through the Spotifiy Connect service.
  - In 2022-08 an issue came up that some Spotify APs became non-responsive basically breaking this player completely. And although there existed a workaround using some specially crafted entries in `/etc/hosts` (see this [comment](https://github.com/librespot-org/librespot/issues/972#issuecomment-1195907706) for details) I decided to directly switch to [librespot](https://github.com/librespot-org/librespot) instead (which Spotifyd is based on anyway) since the issue had already been fixed in code there only a few days after it had been discovered.
  - In 2024-08 another issue came up - this time librespot stopped working. And since by now [go-librespot](https://github.com/devgianlu/go-librespot) seemed to be maintained a lot better than librespot (and since it includes its own API that is very accessible and allowed me to drop Tekore for good) I decided to switch to go-librespot.
    - To quickly make some changes to allow the internal Spotify Connect Web UI (see below) to get an access token from go-librespot, I made my own [fork of go-librespot](https://github.com/felixstorm/go-librespot) (but this might not be neccessary anymore in the future if go-librespot includes this functionality itself).

- Spotify Connect Web UI
  - Web UI accessible on http://<player_ip_address> without any authentication, so only use within safe environments/networks!
  - Copied from https://github.com/FreekBes/spotify_web_controller
  - Made a few changes to better support the Qudio scenario.
  - nginx (provided by DietPi, will automatically include PHP) serves this (almost) static web application.
  - Web UI completely runs within client web browser, it only gets its Spotify access token from the server through one single php file.
  - It might be helpful to generate a QR code for the link to the web UI and stick that to the outside of the player to be able to access it easily with a mobile phone.


## Installation

- DietPi (based on v8.7)
  - Get DietPi Raspberry Pi image from https://dietpi.com/ (ARMv6 32-bit image for Pi Zero)
  - Burn image to an SD card with `dd` (Linux), `rufus` (Windows) or similar
  - Before first start, copy the `/boot` directory from this repo to the first partition of the SD card (overwriting existing files) and
    - adjust in `dietpi.txt`:
      - Hostname (`AUTO_SETUP_NET_HOSTNAME`)
      - Authorized SSH key (`AUTO_SETUP_SSH_PUBKEY`)
      - potentially also lines containing `QTEST`
    - rename `dietpi-wifi.txt.sample` to `dietpi-wifi.txt` and add your WiFi credentials

- Wait for DietPi First Run Setup to complete
  - This takes quite some time, on my Pi Zero it takes more than 1 hour.
  - Potentially helpful commands:
    ```sh
    tail -fn10000 /var/tmp/dietpi/logs/dietpi-update.log
    tail -fn10000 /var/tmp/dietpi/logs/dietpi-firstrun-setup.log
    # if unsure, use htop to check what is really happening
    htop
    ```
  - Also check `/var/tmp/dietpi/logs/dietpi-automation_custom_script.log` for any errors.

- Copy Qudio files
  - Only works from Linux (and partly even only on `x86_64`). If you are on Windows, try using WSL2 instead, but make sure to also `git clone` from within WSL2 to ensure correct executable flags on the files.
  - Create the file `mnt/dietpi_userdata/qudio/qudio.ini` from `qudio.ini.sample`. This is where you get the required values from:
    - `SPOTIFY_DEVICE_NAME`: The name that `librespot` will use to advertise its services - choose as you like.
  - As [Spotify authentication with username and password does not work anymore](https://github.com/librespot-org/librespot/issues/1308), we need to provide a file with cached credentials for go-librespot to work (instead of the literal username and password as had been done before). The file can most easily be created by running go-librespot locally and make use of its interactive authentication feature. From your Linux box, run `.develop/create_golibrespot_credentials.sh` and open the link provided in the console output with a browser that is logged in to the correct Spotify account. After the authentication has been confirmed in the browser, go-librespot will save the credentials to `.develop/go-librespot-credentials.json` immediately and can be exited thereafter using Ctrl-C. Copy this file to `mnt/dietpi_userdata/qudio` also.
  - From your Linux box, run `.develop/push_to_device.sh 192.168.x.y` to copy the files to the Raspberry Pi Zero and to automatically run the script `install.sh` there after copying.
  - Reboot RPi to see if everything works (connect with SSH/Putty): `systemctl reboot`
  - After restart run `journalctl -n10000` and check logs for errors (some minor errors are to be expected)

- Edit `/etc/fstab` and change `/` and `/boot` mounts from `rw` to `ro`: `nano /etc/fstab`
  - Reboot RPi again to see if everything still works: `systemctl reboot`
  - After restart run `journalctl -n10000` again and check logs


## Update DietPi, APT packages and Python packages later
Connect to device using SSH (or Putty), then enter the following commands:  
```bash
# First remount both root and boot file systems read-write
mount -o rw,remount /; mount -o rw,remount /boot
# Then run `dietpi-update` to upgrade DietPi and APT packages (skip reboot)
dietpi-update
# Upgrade Python `pip` to latest version
/usr/bin/python3 -m pip install --upgrade pip
# Show outdated Python packages
pip list --outdated
# Upgrade outdated Python packages, might need to run this twice to update (almost) all
pip list --outdated --format=json | /usr/bin/python3 -c "import json, sys; print('\n'.join([x['name'] for x in json.load(sys.stdin)]))" | xargs -n1 pip install -U
# Now reboot
systemctl reboot
```
After the final reboot, the updates should have all been applied and the filesystem should automatically be mounted read-only again.
