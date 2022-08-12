#!/usr/bin/env python3

import asyncio
from datetime import datetime
from enum import Enum
import logging
import os
from pathlib import Path
import socket
import time

import qudiolib

if qudiolib.IS_RPI:
    from luma.core.interface.serial import i2c
    from luma.oled.device import sh1106
else:
    from luma.emulator.device import pygame
from PIL import Image, ImageDraw, ImageFont

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


this_dir = os.path.dirname(__file__)
# TBD DEFAULT_FONT_PATH = os.path.join(this_dir, "OpenSans-Regular.ttf")
CLOCK_FONT_PATH = os.path.join(this_dir, "OpenSans-SemiBold.ttf")


async def main_async(tk_spotify, tk_player_args):
    logging.info(f'Starting')

    display_player_info_at = 0

    spot_is_playing_last = False
    spot_is_playing_last_time = 0
    update_metadata_last_time = 0

    track_started_at = -1
    track_position = -1
    track_length = -1

    display = DisplayHelper()

    def update_player_display():
        nonlocal display_player_info_at
        logging.debug(f'display_player_info: display_player_info_at = {display_player_info_at}')
        display_player_info_at = time.time() + 0.5
    tmp_file_event_handler = LibrespotTmpFileEventHandler()
    tmp_file_event_handler.begin(update_player_display)

    try:
        while True:
            now = time.time()

            spot_is_playing, local_position, local_duration, local_started_at = qudiolib.spot_get_local_status()
            if spot_is_playing:
                spot_is_playing_last_time = now
            player_is_alive = spot_is_playing_last_time + 30 > now

            logging.debug(
                f'spot_is_playing: {spot_is_playing} (was: {spot_is_playing_last}), spot_is_playing_last_time: {spot_is_playing_last_time} (now: {now}), player_is_alive: {player_is_alive}')

            display.set_mode(DisplayHelper.Mode.PLAYER if player_is_alive else DisplayHelper.Mode.STANDBY)

            if player_is_alive:

                update_metadata = (display_player_info_at > 0 and now >= display_player_info_at) or \
                    now > update_metadata_last_time + 10
                logging.debug(
                    f'update_metadata: {update_metadata}, display_player_info_at: {display_player_info_at}, update_metadata_last_time: {update_metadata_last_time} (now: {now})')
                if update_metadata:

                    playback_state = await qudiolib.spot_get_playback_state_async(tk_spotify, tk_player_args["device_id"])
                    if playback_state is not None and playback_state.item is not None:
                        item = playback_state.item
                        artist = item.artists[0].name if item.artists is not None else ""
                        title = item.name
                        display.update_metadata(artist, title, playback_state.shuffle_state)

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

                    display_player_info_at = 0  # just in case this was our trigger
                    update_metadata_last_time = now

                if spot_is_playing and local_started_at is not None:
                    track_started_at = local_started_at
                    track_position = -1
                if local_duration is not None:
                    track_length = local_duration

                if track_started_at >= 0 or track_position >= 0:
                    position_secs = track_position if track_position >= 0 else time.time() - track_started_at
                    display.update_position(position_secs, track_length)

            display.update_other()

            spot_is_playing_last = spot_is_playing

            next_frame_delay = 1 - (time.time() - now)
            if next_frame_delay >= 0:
                await asyncio.sleep(next_frame_delay)

    finally:
        tmp_file_event_handler.end()
        logging.info('Exiting')


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
        if qudiolib.IS_RPI:
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

    def update_metadata(self, artist, title, shuffle_state):
        if self.current_mode == DisplayHelper.Mode.PLAYER:
            logging.info(f'update_metadata(): {artist} - {title}, shuffle: {shuffle_state}')
            y_offset = 5
            self.clear(line_start=1, line_count=2, y0=y_offset)
            self.text(artist, line=1, y=y_offset)
            self.text(title, line=2, y=y_offset)
            y_offset = 9
            if shuffle_state:
                self.text_ra('S', line=3, y=y_offset)
            else:
                self.clear(line_start=3, y0=y_offset, line_count=1, x0=127-6)

    def update_position(self, position_secs, track_length):
        if self.current_mode == DisplayHelper.Mode.PLAYER:

            if self.needs_redraw or position_secs != self.position_secs_last or track_length != self.track_length_last:
                logging.debug(f'update_position(): {position_secs} / {track_length}')

                y_offset = 9
                self.clear(line_start=3, line_count=1, y0=y_offset, x1=127-6)
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


class LibrespotTmpFileEventHandler(FileSystemEventHandler):

    def begin(self, on_event_func):
        Path(qudiolib.LIBRESPOT_EVENT_FOLDER).mkdir(parents=True, exist_ok=True)
        self.on_event_func = on_event_func
        self.observer = Observer()
        self.observer.schedule(self, path=qudiolib.LIBRESPOT_EVENT_FOLDER, recursive=False)
        self.observer.start()

    def end(self):
        self.observer.stop()
        self.observer.join()

    def on_modified(self,  event):
        if event.src_path == qudiolib.LIBRESPOT_EVENT_FULLNAME:
            self.on_event_func()
