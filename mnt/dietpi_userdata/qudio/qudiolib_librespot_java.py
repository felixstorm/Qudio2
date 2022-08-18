#!/usr/bin/env python3

import asyncio
import httpx
import json
import logging
import os
import time
from types import SimpleNamespace
import websockets


this_dir = os.path.dirname(__file__)
IS_RPI = os.path.isdir("/boot/dietpi")
LIBRESPOT_JAVA_API_ADDRESS = 'localhost:24879'

state = SimpleNamespace()
state.is_playing = None
state.track_started_at = None
state.position = None
state.duration = None
state.artist = None
state.title = None
state.metadata_updated_at = None


async def main_async():

    logging.info(f'Starting')

    async with httpx.AsyncClient() as client:
        # dirty hack to be able to detect if playing or not :-(
        current_pre_response = await client.post(f'http://{LIBRESPOT_JAVA_API_ADDRESS}/player/current')
        current_pre = json.loads(current_pre_response.text)
        logging.debug(f'current_pre: {current_pre_response.text}')
        await asyncio.sleep(0.5)

        current_response = await client.post(f'http://{LIBRESPOT_JAVA_API_ADDRESS}/player/current')
        current = json.loads(current_response.text)
        logging.debug(f'current: {current_response.text}')
        
        state.is_playing = current.get('trackTime', 0) != current_pre.get('trackTime', 0)
        if 'trackTime' in current:
            update_position(current['trackTime'])
        if 'track' in current:
            update_metadata(current['track'])

        logging.info(f'state: {state}')

    async with websockets.connect(f'ws://{LIBRESPOT_JAVA_API_ADDRESS}/events', ping_interval=None, close_timeout=1) as api_websocket:

        while True:
            try:
                message_raw = await asyncio.wait_for(api_websocket.recv(), 1.0)
                logging.debug(f'message_raw: {message_raw}')

                try:
                    message = json.loads(message_raw)
                    match message['event']:
                        case 'playbackResumed':
                            state.is_playing = True
                        case 'playbackPaused':
                            state.is_playing = False
                        case 'playbackEnded':
                            state.is_playing = False
                            update_metadata()
                        case 'inactiveSession':
                            state.is_playing = False
                            if state.track_started_at is not None:
                                state.position = time.time() - state.track_started_at
                        case 'trackChanged':
                            if message['userInitiated'] == False:
                                state.is_playing = True
                                update_position(0)
                        case 'metadataAvailable':
                            update_metadata(message.get('track', None))
                        case 'playbackHaltStateChanged':
                            state.is_playing = not message['halted']
                        case 'contextChanged' | 'volumeChanged' | 'sessionChanged' | 'sessionCleared' | 'connectionEstablished' | 'connectionDropped':
                            continue # irrelevant for now
                        case _:
                            logging.warning(f'Unknown message: {json.dumps(message)}')

                    if 'trackTime' in message:
                        update_position(message['trackTime'])

                    logging.info(f'state: {state}')

                except BaseException as err:
                    logging.exception(err)

            except (asyncio.CancelledError, SystemExit):
                raise

            except asyncio.TimeoutError:
                pass


def update_position(track_time):
    if track_time >= 0:
        state.position = track_time / 1000
        state.track_started_at = time.time() - state.position

def update_metadata(track = None):
    state.duration = track['duration'] / 1000 if 'duration' in track else None
    state.artist = ', '.join([t['name'] for t in track['artist']]) if 'artist' in track else ''
    state.title = track.get('name', '')
    state.metadata_updated_at = time.time()
