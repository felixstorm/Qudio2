#!/usr/bin/env python3

import json
import aiohttp
import asyncio
import logging
import os
import time
from types import SimpleNamespace


IS_RPI = os.path.isdir("/boot/dietpi")
LIBRESPOT_JAVA_API_ADDRESS = 'localhost:24879'


librespot_is_alive_event = asyncio.Event()

state = SimpleNamespace()
state.is_playing = None
state.track_started_at = None
state.position = None
state.duration = None
state.artist = None
state.title = None
state.metadata_updated_at = None
state.shuffle = False


async def main_async():

    logging.info('Starting')

    try:
        global http_client_session
        async with aiohttp.ClientSession(f'http://{LIBRESPOT_JAVA_API_ADDRESS}') as http_client_session:


            for try_count in reversed(range(10)):
                try:
                    player_status_pre = await player_get_current_state()
                except Exception as err:
                    if try_count == 0:
                        raise
                    logging.error(f"{type(err).__name__} connecting to librespot-java API: {err}")
                    time.sleep(1)
                    continue
                break

            # ugly hack to determine if player is playing or paused
            await asyncio.sleep(0.5)
            player_status_now = await player_get_current_state()

            state.is_playing = player_status_now.get('trackTime', 0) != player_status_pre.get('trackTime', 0)
            if 'trackTime' in player_status_now:
                __update_position(player_status_now['trackTime'])
            if 'track' in player_status_now:
                __update_metadata(player_status_now['track'])

            logging.info(f'state: {state}')


            async with http_client_session.ws_connect('/events') as api_websocket:
                
                librespot_is_alive_event.set()

                async for websocket_message in api_websocket:

                    if websocket_message.type == aiohttp.WSMsgType.TEXT:
                        logging.debug(f'websocket_message.data: {websocket_message.data}')

                        try:
                            message = websocket_message.json()
                            event = message['event']
                            # no Python 3.10 yet on the Pi :-(
                            if event == 'playbackResumed':
                                state.is_playing = True
                            elif event == 'playbackPaused':
                                state.is_playing = False
                            elif event == 'playbackEnded':
                                state.is_playing = False
                                __update_metadata()
                            elif event == 'inactiveSession':
                                state.is_playing = False
                                if state.track_started_at is not None:
                                    state.position = time.time() - state.track_started_at
                            elif event == 'trackChanged':
                                if message['userInitiated'] == False:
                                    state.is_playing = True
                                    __update_position(0)
                            elif event == 'metadataAvailable':
                                __update_metadata(message.get('track', None))
                            elif event == 'playbackHaltStateChanged':
                                state.is_playing = not message['halted']
                            elif event in ['contextChanged', 'volumeChanged', 'sessionChanged', 'sessionCleared', 'connectionEstablished', 'connectionDropped']:
                                continue # irrelevant for now
                            else:
                                logging.warning(f'Unknown message: {websocket_message.data}')

                            if 'trackTime' in message:
                                __update_position(message['trackTime'])

                            logging.info(f'state: {state}')

                        except Exception as exception:
                            logging.exception(exception)

                    elif websocket_message.type == aiohttp.WSMsgType.ERROR:
                        raise websocket_message.data


    finally:
        logging.info('Exiting')


def __update_position(track_time):
    if track_time >= 0:
        state.position = track_time / 1000
        state.track_started_at = time.time() - state.position

def __update_metadata(track = None):
    if track is None:
        state.duration = state.artist = state.title = None
    else:
        state.duration = track['duration'] / 1000 if 'duration' in track else None
        state.artist = ', '.join([t['name'] for t in track['artist']]) if 'artist' in track else ''
        state.title = track.get('name', '')
    state.metadata_updated_at = time.time()

def get_current_position_secs():
    if not state.is_playing:
        return state.position
    elif state.track_started_at is not None:
        return time.time() - state.track_started_at
    else:
        return None


async def player_get_current_state():
    async with http_client_session.post('/player/current') as http_response:
        logging.debug(f'http_response: {http_response.status} / {http_response.content_type} / {await http_response.text()}')
        return await http_response.json(content_type=None) # ignore content-type as API returns application/octet-stream

async def player_update_shuffle_state():
    async with http_client_session.get('/web-api/v1/me/player') as http_response:
        # logging.debug(f'http_response: {http_response.status} / {http_response.content_type} / {await http_response.text()}')
        try:
            state.shuffle = (await http_response.json()).get('shuffle_state')
        except:
            state.shuffle = False


async def player_start_context(context):
    await http_client_session.post('/player/load', params={'uri': context, 'play': 'true'})

async def player_play_pause():
    await http_client_session.post('/player/play-pause')

async def player_previous():
    await http_client_session.post('/player/prev')

async def player_next():
    await http_client_session.post('/player/next')

async def player_seek_delta(delta_secs):
    current_position_secs = get_current_position_secs()
    if current_position_secs is not None:
        new_position_ms = (current_position_secs + delta_secs) * 1000
        await http_client_session.post('/player/load', params={'pos': int(new_position_ms)})


async def player_shuffle_toggle():
    await player_update_shuffle_state()
    new_state = not state.shuffle
    logging.debug(f'state.shuffle: {state.shuffle}, new_state: {new_state}')
    # params do not support boolean values, need empty body for librespot-java to process it
    await http_client_session.put('/web-api/v1/me/player/shuffle', params={'state': json.dumps(new_state)}, json={})
    state.shuffle = new_state
