@setlocal
@pushd %~dpn0

@set SOURCE_FOLDER=..\qudio\code\sounds
@set TARGET_FOLDER=mnt\dietpi_userdata\qudio\sounds

ffmpeg -i %SOURCE_FOLDER%\scanning.mp3 -acodec pcm_u8 -ar 22050 %TARGET_FOLDER%\scanning.wav
ffmpeg -i %SOURCE_FOLDER%\ok.mp3 -acodec pcm_u8 -ar 22050 %TARGET_FOLDER%\ok.wav
ffmpeg -i %SOURCE_FOLDER%\fail.mp3 -acodec pcm_u8 -ar 22050 %TARGET_FOLDER%\fail.wav
ffmpeg -i %SOURCE_FOLDER%\volumio-startup.wav -filter:a "volume=21dB" -acodec pcm_u8 -ar 22050 %TARGET_FOLDER%\startup.wav

@pause