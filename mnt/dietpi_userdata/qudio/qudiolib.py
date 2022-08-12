#!/usr/bin/env python3

# based on http://www.tilman.de/projekte/qudio

import configparser
import logging
import os
import time

import tekore as tk


# Configuration
this_dir = os.path.dirname(__file__)
IS_RPI = os.path.isdir("/boot/dietpi")
QUDIO_INI_FILE = os.getenv('QUDIO_INI', os.path.join(this_dir, "qudio.ini"))
LIBRESPOT_EVENT_FOLDER = "/tmp/librespot"
LIBRESPOT_EVENT_FULLNAME = os.path.join(LIBRESPOT_EVENT_FOLDER, "event")


def spot_get_spotify():
    # connect to Spotify Web API
    tk_conf = [c.strip('"') for c in tk.config_from_file(QUDIO_INI_FILE, "tekore", return_refresh=True)]
    tk_token = tk.refresh_user_token(*tk_conf[:2], tk_conf[3])
    tk_spotify = tk.Spotify(tk_token, asynchronous=True)
    return tk_spotify


async def spot_get_player_id_async(tk_spotify):
    # get local Spotify Connect device name
    config = configparser.ConfigParser()
    config.read(QUDIO_INI_FILE)
    local_player_name = config["librespot"]["SPOTIFY_DEVICE_NAME"].strip('"') or "Librespot"
    logging.info(f"Found local Spotify Connect Player name to be '{local_player_name}'")

    for try_count in reversed(range(15)):
        tk_devices = await tk_spotify.playback_devices()
        logging.info("Currently Active Spotify Connect Devices:")
        for tk_device in tk_devices:
            logging.info(tk_device)
        tk_local_device = next((x for x in tk_devices if x.name == local_player_name), None)
        if tk_local_device is not None:
            break
        error_message = f"Unable to find local Spotify Connect device named '{local_player_name}'"
        if try_count == 0:
            raise Exception(error_message)
        logging.error(f"{error_message}, delaying and retrying...")
        time.sleep(1)

    logging.info(f"Using Spotify Connect device '{tk_local_device.name}' with id {tk_local_device.id}")
    return tk_local_device.id


async def spot_get_player_args_async(tk_spotify):
    tk_player_id = await spot_get_player_id_async(tk_spotify)
    tk_player_args = {"device_id": tk_player_id}
    return tk_player_args


def spot_get_local_status():
    event = position = duration = started_at = None
    try:
        with open(LIBRESPOT_EVENT_FULLNAME, "r") as file:
            for index, line in enumerate(file):
                line = line.strip()
                if index == 0:
                    event = line
                elif index == 1 and line != "" and line != "0":  # position is sometimes written as 0 even though the song is already playing in the middle
                    position = float(line) / 1000
                elif index == 2 and line != "":
                    duration = float(line) / 1000
        if position is not None:
            started_at = os.path.getmtime(LIBRESPOT_EVENT_FULLNAME) - position
    except FileNotFoundError:
        pass
    except BaseException as err:
        logging.warning(f"Unexpected {type(err)}: {err}")
    is_playing = event == "start" or event == "play" or event == "change" or event == "endoftrack" # spotifyd
    is_playing |= event == "started" or event == "playing" or event == "changed"                   # librespot
    logging.debug(
        f"spot_get_local_status(): event: '{event}', is_playing: {is_playing}, position: {position}, started_at: {started_at}, duration: {duration}")
    return is_playing, position, duration, started_at


def spot_get_is_playing():
    return spot_get_local_status()[0]


async def spot_get_playback_state_async(tk_spotify, local_device_id=None):
    playback_state = await tk_spotify.playback()
    logging.debug(playback_state)
    if playback_state is not None:
        logging.debug(playback_state.item)

    playback_state_device_id = playback_state and playback_state.device and playback_state.device.id
    logging.debug(f"local_device_id: '{local_device_id}', playback_state_device_id: {playback_state_device_id}")
    if playback_state_device_id != local_device_id:
        return None

    return playback_state
