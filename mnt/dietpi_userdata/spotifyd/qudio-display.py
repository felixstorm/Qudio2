#!/usr/bin/env python3

import os
IS_RPI = os.path.isdir("/boot/dietpi")
import logging
from enum import Enum
from pathlib import Path
import time
import signal
from datetime import datetime
import socket

import qudiolib

if IS_RPI:
    from luma.core.interface.serial import i2c
    from luma.oled.device import sh1106
else:
    from luma.emulator.device import pygame
from PIL import Image, ImageDraw, ImageFont

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# TBD DEFAULT_FONT_PATH = os.path.join(os.path.dirname(__file__), "OpenSans-Regular.ttf")
CLOCK_FONT_PATH = os.path.join(os.path.dirname(__file__), "OpenSans-SemiBold.ttf")


def main():
    logging.basicConfig(format=',%(msecs)03d %(levelname)-5.5s [%(filename)-12.12s:%(lineno)3d] %(message)s',
                        level=os.environ.get('LOGLEVEL', 'INFO').upper())
    logging.info(f'Starting using path "{qudiolib.SPOTD_EVENT_FILE}"')
    Path(qudiolib.SPOTD_EVENT_FOLDER).mkdir(parents=True, exist_ok=True)

    PlayerHelper().run()

    logging.info('Exiting')


class PlayerHelper:
    thread_should_stop = False
    display_player_info_at = 0

    def run(self):
        self.display = DisplayHelper()

        signal.signal(signal.SIGINT, self.signal)
        signal.signal(signal.SIGTERM, self.signal)

        self.tmp_file_event_handler = SpotifydTmpFileEventHandler()
        self.tmp_file_event_handler.begin(self.update_player_display)

        if IS_RPI:
            self.spot_spotify = qudiolib.spot_get_spotify()
            self.spot_player_id = qudiolib.spot_get_player_id(self.spot_spotify)

        spot_is_playing_last = False
        spot_is_playing_last_time = 0
        update_metadata_last_time = 0

        track_started_at = -1
        track_position = -1
        track_length = -1

        while not self.thread_should_stop:
            now = time.time()

            spot_is_playing, local_position, local_duration, local_started_at = qudiolib.spot_get_local_status()
            if spot_is_playing:
                spot_is_playing_last_time = now
            player_is_alive = spot_is_playing_last_time + 30 > now

            logging.debug(
                f'spot_is_playing: {spot_is_playing} (was: {spot_is_playing_last}), spot_is_playing_last_time: {spot_is_playing_last_time} (now: {now}), player_is_alive: {player_is_alive}')

            self.display.set_mode(DisplayHelper.Mode.PLAYER if player_is_alive else DisplayHelper.Mode.STANDBY)

            if player_is_alive:

                update_metadata = (self.display_player_info_at > 0 and now >= self.display_player_info_at) or \
                    now > update_metadata_last_time + 10
                logging.debug(
                    f'update_metadata: {update_metadata}, display_player_info_at: {self.display_player_info_at}, update_metadata_last_time: {update_metadata_last_time} (now: {now})')
                if update_metadata:

                    playback_state = qudiolib.spot_get_playback_state(self.spot_spotify, self.spot_player_id)
                    if playback_state is not None and playback_state.item is not None:
                        item = playback_state.item
                        artist = item.artists[0].name if item.artists is not None else ""
                        title = item.name
                        self.display.update_metadata(artist, title)

                        if spot_is_playing:
                            track_started_at = time.time() - playback_state.progress_ms / 1000
                            track_position = -1
                        else:
                            track_started_at = -1
                            track_position = playback_state.progress_ms / 1000
                        track_length = item.duration_ms / 1000

                    else:
                        track_started_at = -1
                        track_position = -1
                        track_length = -1

                    self.display_player_info_at = 0  # just in case this was our trigger
                    update_metadata_last_time = now

                if spot_is_playing and local_started_at is not None:
                    track_started_at = local_started_at
                    track_position = -1
                if local_duration is not None:
                    track_length = local_duration

                if track_started_at >= 0 or track_position >= 0:
                    position_secs = track_position if track_position >= 0 else time.time() - track_started_at
                    self.display.update_position(position_secs, track_length)

            self.display.update_other()

            spot_is_playing_last = spot_is_playing
            time.sleep(1 - (time.time() - now))

        self.tmp_file_event_handler.end()

    def update_player_display(self):
        logging.debug(f'display_player_info: display_player_info_at = {self.display_player_info_at}')
        self.display_player_info_at = time.time() + 0.5

    def signal(self, *args):
        self.thread_should_stop = True


class DisplayHelper:

    class Mode(Enum):
        UNDEFINED = -1
        STANDBY = 0
        PLAYER = 1

    current_mode = Mode.UNDEFINED
    needs_redraw = True
    position_secs_last = -1
    track_length_last = -1
    now_string_last = ""

    def __init__(self):
        if IS_RPI:
            oled_i2c = i2c(port=1, address=0x3C)
            self.oled_device = sh1106(oled_i2c, rotate=2)
        else:
            self.oled_device = pygame(mode='1', transform='smoothscale', scale=4, frame_rate=10)
        self.oled_image = Image.new(self.oled_device.mode, self.oled_device.size, 'black')
        self.oled_draw = ImageDraw.Draw(self.oled_image)
        self.lh = 11
        self.default_font = None  # TBD ImageFont.truetype(DEFAULT_FONT_PATH, 11)
        self.clock_font = ImageFont.truetype(CLOCK_FONT_PATH, 48)

    def set_mode(self, new_mode):
        if new_mode != self.current_mode:
            self.needs_redraw = True
            self.oled_draw.rectangle((0, 0, 127, 63), fill='black')
            self.current_mode = new_mode

    def update_metadata(self, artist, title):
        if self.current_mode == DisplayHelper.Mode.PLAYER:
            logging.info(f'update_metadata(): {artist} - {title}')
            y_offset = 5
            self.clear(line_start=1, line_count=2, y0=y_offset)
            self.text(artist, line=1, y=y_offset)
            self.text(title, line=2, y=y_offset)

    def update_position(self, position_secs, track_length):
        if self.current_mode == DisplayHelper.Mode.PLAYER:

            if self.needs_redraw or position_secs != self.position_secs_last or track_length != self.track_length_last:
                logging.debug(f'update_position(): {position_secs} / {track_length}')

                y_offset = 9
                self.clear(line_start=3, line_count=1, y0=y_offset)
                pos_text = f'Pos: {time.strftime("%M:%S", time.gmtime(position_secs))} / {time.strftime("%M:%S", time.gmtime(track_length))}'
                self.text(pos_text, line=3, y=y_offset)

                if track_length > 0:
                    rect_x1 = position_secs / track_length * 127
                    update_only = not self.needs_redraw and position_secs > self.position_secs_last
                    logging.debug(
                        f'update_position(): update_only: {update_only} (needs_redraw: {self.needs_redraw}, position_secs: {position_secs}, position_secs_last: {self.position_secs_last})')
                    if update_only:
                        rect_x0 = self.position_secs_last / self.track_length_last
                    else:
                        self.rect(line_start=4, line_count=1, y0=y_offset, fill='black', outline='white')
                        rect_x0 = 0
                    self.rect(x0=rect_x0, x1=rect_x1, line_start=4, line_count=1, y0=y_offset)

                self.position_secs_last = position_secs
                self.track_length_last = track_length

    def update_other(self, send_to_display=True):
        if self.current_mode != DisplayHelper.Mode.UNDEFINED:

            now_string = datetime.now().strftime('%H:%M')
            if self.needs_redraw or now_string != self.now_string_last:
                logging.debug(
                    f"update_other(): needs_redraw: {self.needs_redraw}, now_string: '{now_string}', now_string_last: '{self.now_string_last}'")

                if self.current_mode == DisplayHelper.Mode.PLAYER:
                    self.clear(line_count=1, y0=0)
                    self.text(self.get_local_ip(), y=0)
                    self.text_ra(now_string, y=0)

                elif self.current_mode == DisplayHelper.Mode.STANDBY:
                    self.clear(y0=0, y1=63)
                    self.text_ca(now_string, y=-10, font=self.clock_font)
                    self.text_ra(self.get_local_ip(), y=63-self.lh)

                self.now_string_last = now_string

            if send_to_display:
                self.send_to_display()

    def send_to_display(self):
        self.oled_device.display(self.oled_image)
        self.needs_redraw = False

    def rect(self, line_start=None, line_count=None, y0=0, y1=None, x0=0, x1=127, fill='white', outline=None, width=1):
        if line_start is not None:
            y0 += line_start * self.lh
        if y1 is None:
            y1 = y0
        if line_count is not None:
            y1 += line_count * self.lh - 1
        self.oled_draw.rectangle((x0, y0, x1, y1), fill=fill, outline=outline, width=width)

    def clear(self, line_start=None, line_count=None, y0=0, y1=None, x0=0, x1=127):
        self.rect(line_start=line_start, line_count=line_count, y0=y0, y1=y1, x0=x0, x1=x1, fill='black')

    def text(self, text, line=None, x=0, y=0, font=None):
        if line is not None:
            y += line * self.lh
        if font is None:
            font = self.default_font
            # remove all characters invalid in Latin-1 as PIL default font does only seem to contain Latin-1 code page
            text = bytes(text,'iso-8859-1', 'replace').decode('iso-8859-1')
        self.oled_draw.text((x, y), text, fill='white', font=font)

    def text_ra(self, text, line=None, y=None, font=None):
        textsize = self.oled_draw.textsize(text, font=font)
        self.text(text, line=line, x=128-textsize[0], y=y, font=font)

    def text_ca(self, text, line=None, y=None, font=None):
        textsize = self.oled_draw.textsize(text, font=font)
        self.text(text, line=line, x=64-textsize[0]/2, y=y, font=font)

    def get_local_ip(self):
        st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            st.connect(('10.255.255.255', 1))
            IP = st.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            st.close()
        return IP


class SpotifydTmpFileEventHandler(FileSystemEventHandler):

    def begin(self, on_event_func):
        self.on_event_func = on_event_func
        self.observer = Observer()
        self.observer.schedule(self, path=qudiolib.SPOTD_EVENT_FOLDER, recursive=False)
        self.observer.start()

    def end(self):
        self.observer.stop()
        self.observer.join()

    def on_modified(self,  event):
        if event.src_path == qudiolib.SPOTD_EVENT_FILE:
            self.on_event_func()


main()
