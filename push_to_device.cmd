@setlocal
@set PROMPT=$G
@cls

@if "%~1" == "" exit /b

@net use w: /d 2>nul
net use w: \\sshfs.r\root@%1 dietpi
@if errorlevel 1 exit /b

plink root@%1 -pw dietpi mount -o remount rw /; mount -o remount rw /boot

robocopy /e /njh /xx %~dp0\etc w:\etc
robocopy /e /njh /xx %~dp0\mnt w:\mnt

@if not exist w:\mnt\dietpi_userdata\spotifyd\spotifyd_creds.sh (
    notepad w:\mnt\dietpi_userdata\spotifyd\spotifyd.conf
    pause
)

plink root@%1 -pw dietpi /mnt/dietpi_userdata/spotifyd/install.sh

if not "%~1" == "192.168.0.142" plink root@%1 -pw dietpi mount -o remount ro /; mount -o remount ro /boot

plink root@%1 -pw dietpi systemctl restart spotifyd.service; systemctl start qudio-control.service qudio-display.service

net use w: /d
