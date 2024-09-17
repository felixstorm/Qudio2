#!/usr/bin/env python3

import asyncio
import logging
import os
import signal

import qudiolib
import qudio_control
import qudio_display

global tasks


async def main_async():
    logging.basicConfig(format=',%(msecs)03d %(levelname)-5.5s [%(filename)-12.12s:%(lineno)3d] %(message)s',
                        level=os.environ.get('LOGLEVEL', 'INFO').upper())

    logging.info('Connect to go-librespot')
    async with qudiolib.QudioPlayerGoLibreSpot() as qudio_player:

        tasks=[
            asyncio.create_task(qudiolib.run_forever(qudio_control.main_async, 5, qudio_player)),
            asyncio.create_task(qudiolib.run_forever(qudio_display.main_async, 5, qudio_player)),
        ]

        def handler(signum, _):
            logging.info(f'Received signal {signum}')
            for task in tasks:
                task.cancel()
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

        await asyncio.wait(tasks)

    logging.info('Exiting')


asyncio.run(main_async())
