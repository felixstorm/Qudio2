#!/usr/bin/env python3

import asyncio
import logging
import os
import signal

import qudiolib_librespot_java as qudiolib
import qudio_control
import qudio_display

global tasks


async def main_async():
    # logging.basicConfig(format='%(asctime)s %(levelname)-5.5s [%(filename)-12.12s:%(lineno)3d] %(message)s',
    logging.basicConfig(format=',%(msecs)03d %(levelname)-5.5s [%(filename)-12.12s:%(lineno)3d] %(message)s',
                        level=os.environ.get('LOGLEVEL', 'INFO').upper())
    logging.info(f'Starting')

    tasks = []
    def signal_handler(signum, frame):
        logging.info(f'Received signal {signum}')
        for task in tasks:
            task.cancel()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    async def run_forever(coroutine):
        while True:
            try:
                await coroutine()
            except (asyncio.CancelledError, SystemExit):
                break
            except BaseException as exception:
                logging.exception(exception)
            await asyncio.sleep(5)

    tasks.append(asyncio.create_task(run_forever(qudiolib.main_async)))
    tasks.append(asyncio.create_task(run_forever(qudio_control.main_async)))
    tasks.append(asyncio.create_task(run_forever(qudio_display.main_async)))

    await asyncio.wait(tasks)

    logging.info('Exiting')


asyncio.run(main_async())
