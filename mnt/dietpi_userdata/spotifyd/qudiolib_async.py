#!/usr/bin/env python3

# based on http://www.tilman.de/projekte/qudio

import asyncio
import logging
import os
import configparser

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
    tk_spotify = tk.Spotify(tk_token, asynchronous=True)
    return tk_spotify


async def spot_get_player_id(tk_spotify):
    # get local Spotify Connect device name
    config = configparser.ConfigParser()
    config.read(SPOTD_CONF)
    local_player_name = config["global"]["device_name"].strip('"') or "Spotifyd"
    logging.info(f"Found local Spotify Connect Player name to be '{local_player_name}'")

    attempts = 0
    while True:
        attempts += 1
        tk_devices = await tk_spotify.playback_devices()
        logging.info("Currently Active Spotify Connect Devices:")
        for tk_device in tk_devices:
            logging.info(tk_device)
        tk_local_device = next((x for x in tk_devices if x.name.startswith(local_player_name)), None)
        if tk_local_device is not None:
            break
        if attempts >= 3:
            raise Exception(f"Unable to find local Spotify Connect device named '{local_player_name}'")
        logging.warning(f"Unable to find local Spotify Connect device named '{local_player_name}', delaying a bit and retrying...")
        await asyncio.sleep(2)

    logging.info(f"Using Spotify Connect device '{tk_local_device.name}' with id {tk_local_device.id}")
    return tk_local_device.id


async def spot_get_player_args(tk_spotify):
    tk_player_id = await spot_get_player_id(tk_spotify)
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


async def spot_get_playback_state(tk_spotify, local_device_id=None):
    playback_state = await tk_spotify.playback()
    logging.debug(playback_state)
    if playback_state is not None:
        logging.debug(playback_state.item)

    if local_device_id is not None and (playback_state is None or playback_state.device is None or playback_state.device.id != local_device_id):
        return None

    return playback_state
