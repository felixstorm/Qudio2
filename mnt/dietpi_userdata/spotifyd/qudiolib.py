#!/usr/bin/env python3

# based on http://www.tilman.de/projekte/qudio

import os
import logging
import configparser

from PIL.Image import NONE

# spotifyd seems to not be able to activate itself as a player (OpenUri will only work if it already is active),
# so we need to use the Spotify Web API directly using tekore.
# also, the binary for RPi 1 / Zero does not include mdbus support at all :-(
import tekore as tk


# Configuration
this_dir = os.path.dirname(__file__)
SPOTD_CONF = os.path.join(this_dir, "spotifyd.conf")
SPOTD_EVENT_FOLDER = "/tmp/spotifyd"
SPOTD_EVENT_FILE = os.path.join(SPOTD_EVENT_FOLDER, "event")


def spot_get_spotify():
    # connect to Spotify Web API
    tk_conf = tk.config_from_file(SPOTD_CONF, "tekore", return_refresh=True)
    tk_conf = [c.strip('"') for c in tk_conf]  # spotifyd.conf requires us to surround values with quotes
    tk_token = tk.refresh_user_token(*tk_conf[:2], tk_conf[3])
    tk_spotify = tk.Spotify(tk_token)
    return tk_spotify


def spot_get_player_id(tk_spotify):
    # get local Spotify Connect device name
    config = configparser.ConfigParser()
    config.read(SPOTD_CONF)
    local_player_name = config["global"]["device_name"].strip('"') or "Spotifyd"
    logging.info(f"Found local Spotify Connect Player name to be '{local_player_name}'")

    tk_devices = tk_spotify.playback_devices()
    logging.debug("Spotify Connect Devices")
    for tk_device in tk_devices:
        logging.debug(tk_device)
    tk_local_device = next(x for x in tk_devices if x.name.startswith(local_player_name))
    logging.info(f"Using Spotify Connect device '{tk_local_device.name}' with id {tk_local_device.id}")
    return tk_local_device.id


def spot_get_player_args(tk_spotify):
    tk_player_id = spot_get_player_id(tk_spotify)
    tk_player_args = {"device_id": tk_player_id}
    return tk_player_args


def spot_get_local_status():
    event = position = duration = started_at = None
    try:
        with open(SPOTD_EVENT_FILE, "r") as file:
            for index, line in enumerate(file):
                line = line.strip()
                if index == 0:
                    event = line
                elif index == 1 and line != "" and line != "0":  # position is sometimes written as 0 even though the song is already playing in the middle
                    position = float(line) / 1000
                elif index == 2 and line != "":
                    duration = float(line) / 1000
        if position is not None:
            started_at = os.path.getmtime(SPOTD_EVENT_FILE) - position
    except FileNotFoundError:
        pass
    except BaseException as err:
        logging.warning(f"Unexpected {type(err)}: {err}")
    is_playing = event == "start" or event == "play" or event == "change" or event == "endoftrack"
    logging.debug(
        f"spot_get_local_status(): event: '{event}', is_playing: {is_playing}, position: {position}, started_at: {started_at}, duration: {duration}")
    return is_playing, position, duration, started_at


def spot_get_is_playing():
    return spot_get_local_status()[0]


def spot_get_playback_state(tk_spotify, local_device_id=None):
    playback_state = tk_spotify.playback()
    logging.debug(playback_state)
    if playback_state is not None:
        logging.debug(playback_state.item)

    if local_device_id is not None and (playback_state is None or playback_state.device is None or playback_state.device.id != local_device_id):
        return None

    return playback_state
