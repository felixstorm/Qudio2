#!/usr/bin/env python3

# based on http://www.tilman.de/projekte/qudio

import asyncio
import logging
from collections import namedtuple
import os
import time

import aiohttp


# Configuration
IS_RPI = os.path.isdir("/boot/dietpi")


# based on https://stackoverflow.com/a/55185488/14226388
async def run_forever(coro, restart_delay, *args, **kwargs):
    while True:
        try:
            await coro(*args, **kwargs)
        except (asyncio.CancelledError, SystemExit):
            break
        except BaseException as err:
            logging.exception(err)
        await asyncio.sleep(restart_delay)


class QudioPlayerGoLibreSpot:

    def __init__(self):
        self.callbacks = []
        self.State = namedtuple('State', ['is_playing', 'position', 'duration', 'started_at', 'shuffle', 'title', 'artist'])
        self.session = aiohttp.ClientSession("http://localhost:3678")


    async def __aenter__(self):
        await self.session.__aenter__()
        self.websocket_task = asyncio.create_task(run_forever(self.websocket_task_runner, 1)),
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        # self.websocket_task.cancel() # TBD: throws exception???
        await self.session.__aexit__(exc_type, exc_value, traceback)


    def add_callback(self, callback):
        self.callbacks.append(callback)

    async def websocket_task_runner(self):
        async with self.session.ws_connect('/events') as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = msg.json()
                    logging.debug(f"websocket_task_runner(): data: {data}")
                    for callback in self.callbacks:
                        callback(data)
                elif msg.type in {aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                    break


    async def get_state(self):
        is_playing = position = duration = started_at = shuffle = artist = title = None
        async with self.session.get("/status") as resp:
            result = await resp.json()
            logging.debug(f"get_is_playing(): result: {result}")
            is_playing = result["paused"] == False and result["stopped"] == False
            shuffle = result["shuffle_context"]
            track = result["track"]
            if track is not None:
                if is_playing:
                    position = track["position"] / 1000
                    started_at = time.time() - position
                duration = track["duration"] / 1000
                title = track["name"]
                artist_names = track["artist_names"]
                artist = artist_names[0] if artist_names is not None and len(artist_names) >= 1 else ""
        return self.State(is_playing, position, duration, started_at, shuffle, title, artist)


    async def playback_start_context(self, context):
        async with self.session.post("/player/play", json={"uri": context}):
            pass

    async def playback_pause(self):
        async with self.session.post("/player/pause"):
            pass

    async def playback_resume(self):
        async with self.session.post("/player/resume"):
            pass

    async def playback_previous(self):
        async with self.session.post("/player/prev"):
            pass

    async def playback_next(self):
        async with self.session.post("/player/next"):
            pass

    async def playback_seek(self, seek_pos_ms):
        async with self.session.post("/player/seek", json={"position": seek_pos_ms}):
            pass

    async def playback_shuffle(self, shuffle_state):
        async with self.session.post("/player/shuffle_context", json={"shuffle_context": shuffle_state}):
            pass
