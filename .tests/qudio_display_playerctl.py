#!/usr/bin/env python3

import time
import signal
import threading


from gi.repository import Playerctl

from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# /tmp/spotifyd/event will be updated by on_song_change_hook
# on_song_change_hook = "/bin/bash -c \"mkdir -p /tmp/spotifyd && echo $(date +\"%F %T\") > /tmp/spotifyd/event\""
monitor_path = "/tmp/spotifyd"
monitor_file = monitor_path + "/event"

# OLED display
olde_i2c = i2c(port=1, address=0x3C)
oled_device = sh1106(olde_i2c)
oled_image = Image.new(oled_device.mode, oled_device.size, "black")
oled_draw = ImageDraw.Draw(oled_image)

# draw static content
oled_draw.rectangle((0, 0, 127, 63), outline="white", fill="black")
oled_draw.rectangle((0, 50, 128, 64), outline="white", fill="white")
oled_draw.text((0, 10), 'Artist', fill="white")
oled_draw.text((0, 20), 'Title', fill="white")

oled_device.display(oled_image)


# # https://stackoverflow.com/a/31464349/14226388
# class GracefulKiller:
#     kill_now = False

#     def __init__(self):
#         signal.signal(signal.SIGINT, self.exit_gracefully)
#         signal.signal(signal.SIGTERM, self.exit_gracefully)

#     def exit_gracefully(self, *args):
#         self.kill_now = True


class PlayerHelper:
    track_length = 0

    def begin(self):
        self.thread = threading.Thread(target=self.thread_function)
        self.thread_should_stop = False
        self.update_display_now = True
        self.thread.start()
        signal.signal(signal.SIGINT, self.signal)
        signal.signal(signal.SIGTERM, self.signal)

    def thread_function(self):
        last_pos_time = 0
        while not self.thread_should_stop:
            now = time.time()
            if self.update_display_now or now - last_pos_time > 5:
                if self.update_display_impl(update_metadata=self.update_display_now):
                    self.update_display_now = False
                last_pos_time = now
            time.sleep(1)

    def update_display(self):
        self.update_display_now = True

    def update_display_impl(self, update_metadata=False):

        try:
            player = Playerctl.Player()
            # print(player.list_properties())
            playback_status = player.props.playback_status
        except:
            return False
        print(f"Status: {playback_status}")

        if playback_status == Playerctl.PlaybackStatus.STOPPED:
            oled_draw.rectangle((0, 10, 128, 40), outline="black", fill="black")

        else:
            if update_metadata:
                metadata = player.props.metadata
                # print(metadata)
                if "xesam:artist" in metadata.keys() and "xesam:title" in metadata.keys():
                    print(f"Now playing: {metadata['xesam:artist'][0]} - {metadata['xesam:title']}")
                    oled_draw.rectangle((0, 10, 128, 30), outline="black", fill="black")
                    oled_draw.text((0, 10), metadata['xesam:artist'][0], fill="white")
                    oled_draw.text((0, 20), metadata['xesam:title'], fill="white")
                if "mpris:length" in metadata.keys():
                    self.track_length = metadata["mpris:length"] / 1000000

            position_secs = player.get_position() / 1000000
            if position_secs != 0:
                print(f"Position: {position_secs} / {self.track_length}")
                oled_draw.rectangle((0, 30, 128, 40), outline="black", fill="black")
                oled_draw.text((0, 30), f"Pos: {position_secs} / {self.track_length}", fill="white")

        oled_device.display(oled_image)

        return True

    def signal(self, *args):
        self.end()

    def join(self):
        self.thread.join()

    def end(self):
        self.thread_should_stop = True
        self.join()


class SpotifydTmpFileEventHandler(FileSystemEventHandler):
    last_event_time = 0

    def begin(self, on_event_func):
        self.on_event_func = on_event_func
        self.observer = Observer()
        self.observer.schedule(self, path=monitor_path, recursive=False)
        self.observer.start()

    def end(self):
        self.observer.stop()
        self.observer.join()

    def on_modified(self,  event):
        if event.src_path == monitor_file:
            now = time.time()
            if (now - self.last_event_time > 2):
                self.last_event_time = now
                self.on_event_func()


# graceful_killer = GracefulKiller()

player_helper = PlayerHelper()
player_helper.begin()

tmp_file_event_handler = SpotifydTmpFileEventHandler()
tmp_file_event_handler.begin(player_helper.update_display)

# last_pos_time = time.time()
# while not graceful_killer.kill_now:
#     time.sleep(1)
#     now = time.time()
#     if now - last_pos_time > 5:
#         player_helper.show_player_position()
#         last_pos_time = now

player_helper.join()

tmp_file_event_handler.end()

print("Exiting")
