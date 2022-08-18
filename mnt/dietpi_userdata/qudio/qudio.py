#!/usr/bin/env python3

import asyncio
import logging
import os
import signal

import qudiolib_librespot_java as qudiolib
# import qudio_control
import qudio_display

global tasks


async def main_async():
    # logging.basicConfig(format='%(asctime)s %(levelname)-5.5s [%(filename)-12.12s:%(lineno)3d] %(message)s',
    logging.basicConfig(format=',%(msecs)03d %(levelname)-5.5s [%(filename)-12.12s:%(lineno)3d] %(message)s',
                        level=os.environ.get('LOGLEVEL', 'INFO').upper())
    logging.info(f'Starting')

    tasks=[
        asyncio.create_task(run_forever(lambda: qudiolib.main_async())),
        # asyncio.create_task(run_forever(lambda: qudio_control.main_async())),
        asyncio.create_task(run_forever(lambda: qudio_display.main_async())),
    ]

    def handler(signum, frame):
        logging.info(f'Received signal {signum}')
        for task in tasks:
            task.cancel()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    await asyncio.wait(tasks)

    logging.info('Exiting')


async def run_forever(coroutine_getter):
    while True:
        try:
            await coroutine_getter()
        except (asyncio.CancelledError, SystemExit):
            break
        except BaseException as err:
            logging.exception(err)
            await asyncio.sleep(5)


asyncio.run(main_async())
