#!/usr/bin/env python3

# based on http://www.tilman.de/projekte/qudio

import asyncio
import logging
import os
from pathlib import Path
import select  # for polling zbarcam, see http://stackoverflow.com/a/10759061/3761783
import subprocess
import threading
import time

import qudiolib_librespot_java as qudiolib

import evdev

if qudiolib.IS_RPI:
    import RPi.GPIO as GPIO


# Configuration
this_dir = os.path.dirname(__file__)
SOUND_STARTUP = os.path.join(this_dir, "sounds/startup.wav")
SOUND_SCANNING = os.path.join(this_dir, "sounds/scanning.wav")
SOUND_SCAN_OK = os.path.join(this_dir, "sounds/ok.wav")
SOUND_SCAN_FAIL = os.path.join(this_dir, "sounds/fail.wav")
QR_SCANNER_TIMEOUT = 4
QR_SCANNER_DELAY_AFTER = 1

# photo sensor on PIN 5, LED on PIN 22
PIN_SENSOR, PIN_LED = 5, 22

# Buttons on PINs 9, 10 and 11
PIN_PREV, PIN_PLAY, PIN_NEXT = 10, 9, 11


async def main_async():

    logging.info(f'Starting')

    try:
        if qudiolib.IS_RPI:
            logging.info('Pepare GPIOs')
            GPIO.setmode(GPIO.BCM)

            logging.info('Attach sensor and LED GPIOs')
            GPIO.setup(PIN_LED, GPIO.OUT)
            GPIO.output(PIN_LED, GPIO.LOW)
            GpioInputAsync(PIN_SENSOR, handler_callback_async=scan_qrcode_async).begin()

            logging.info('Attach button GPIOs')
            button_short_press_commands = {
                PIN_PREV: qudiolib.player_previous,
                PIN_PLAY: qudiolib.player_play_pause,
                PIN_NEXT: qudiolib.player_next,
            }
            button_long_press_commands = {
                PIN_PREV: lambda down_secs: qudiolib.player_seek_delta(delta_secs=-5 * down_secs),
                PIN_PLAY: lambda down_secs: qudiolib.player_shuffle_toggle() if down_secs < 1.4 else None,
                PIN_NEXT: lambda down_secs: qudiolib.player_seek_delta(delta_secs=-5 * down_secs),
            }
            for pin in (PIN_PLAY, PIN_PREV, PIN_NEXT):
                GpioInputAsync(pin, button_short_press_commands=button_short_press_commands,
                            button_long_press_commands=button_long_press_commands).begin()

        if qudiolib.IS_RPI:
            try:
                ir_remote = evdev.InputDevice('/dev/input/event0')
            except:
                ir_remote = None
        else:
            ir_remote = evdev.InputDevice('/dev/input/by-path/platform-i8042-serio-0-event-kbd')
        logging.info("IR remote: %s", ir_remote)

        await qudiolib.librespot_is_alive_event.wait()
        if not qudiolib.state.is_playing:
            await play_sound_start_async(SOUND_STARTUP)

        logging.info('Started')

        if ir_remote:
            ir_commands = {
                'KEY_CHANNELUP':   qudiolib.player_previous,
                'KEY_PLAY':        qudiolib.player_play_pause,
                'KEY_CHANNELDOWN': qudiolib.player_next,
                'KEY_MENU':        qudiolib.player_shuffle_toggle,
                # development only
                'KEY_LEFT':  qudiolib.player_previous,
                'KEY_SPACE': qudiolib.player_play_pause,
                'KEY_RIGHT': qudiolib.player_next,
                'KEY_S':     qudiolib.player_shuffle_toggle,
            }
            async for ir_event in ir_remote.async_read_loop():
                ir_event = evdev.categorize(ir_event)
                logging.debug("Received IR event: %s", ir_event)
                if type(ir_event) == evdev.events.KeyEvent and ir_event.keystate == evdev.events.KeyEvent.key_down:
                    logging.info("Received IR key_down: %s", ir_event.keycode)
                    if type(ir_event.keycode) == str:
                        ir_command = ir_commands.get(ir_event.keycode)
                        ir_command and await ir_command()
        else:
            # just wait forever
            await asyncio.Event().wait()

    finally:
        if qudiolib.IS_RPI:
            logging.info('Reset GPIO configuration')
            GPIO.cleanup()
        logging.info('Exiting')


class GpioInputAsync:
    BOUNCETIME = 0.08
    loop = None

    def __init__(self, pin, handler_callback_async=None, button_short_press_commands=None, button_long_press_commands=None):
        if GpioInputAsync.loop is None:
            GpioInputAsync.loop = asyncio.get_running_loop()
        self.pin = pin
        self.handler_callback_async = handler_callback_async or self.button_callback_async
        self.button_short_press_commands = button_short_press_commands
        self.button_long_press_commands = button_long_press_commands
        self.lock = threading.Lock()

    def begin(self):
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # retry until it really works (since it sometimes failes in the beginning after booting)
        for try_count in reversed(range(10)):
            try:
                GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=self.gpio_event_callback,
                                      bouncetime=int(self.BOUNCETIME * 1000))
            except BaseException as err:
                if try_count == 0:
                    raise
                logging.error(f"GPIO.add_event_detect unexpected {type(err)}: {err}")
                time.sleep(1)
                continue
            break

    def gpio_event_callback(self, channel):
        logging.debug("gpio_event_callback: channel: %d", channel)
        if self.lock.acquire(blocking=False):
            asyncio.run_coroutine_threadsafe(self.gpio_event_callback_async(channel, time.time()), GpioInputAsync.loop)

    async def gpio_event_callback_async(self, channel, event_time):
        logging.debug("gpio_event_callback_async: channel: %d, event_time: %f", channel, event_time)
        try:
            # since GPIO bouncetime only suppresses repeating events, we need to deal with bounce on release ourselves
            bounce_delay = event_time + self.BOUNCETIME - time.time()
            if 0 < bounce_delay < self.BOUNCETIME:
                await asyncio.sleep(bounce_delay)
            state_now = GPIO.input(channel)
            logging.debug("gpio_event_callback_async: bounce_delay: %f, state_now: %d", bounce_delay, state_now)
            if state_now == GPIO.LOW:
                await self.handler_callback_async(channel, event_time)
        except BaseException as err:
            logging.exception(err)
        finally:
            self.lock.release()

    async def button_callback_async(self, channel, time_button_down):
        logging.debug("button_callback_async: channel: %d, time_button_down: %f", channel, time_button_down)
        # 0.5 + 0.5 = 1 second delay for first long action
        time_last_long_action = time_button_down + 0.5
        while GPIO.input(channel) == GPIO.LOW:
            now = time.time()
            # 0.5 seconds delay between subsequent long actons
            if now - time_last_long_action > 0.5:
                command = self.button_long_press_commands.get(channel)
                if command:
                    command_awaitable = command(now - time_button_down)
                    command_awaitable and await command_awaitable
                time_last_long_action = now
            await asyncio.sleep(0.1)
        if time.time() - time_button_down < 1:
            command = self.button_short_press_commands.get(channel)
            if command:
                command_awaitable = command()
                command_awaitable and await command_awaitable


async def play_sound_start_async(wavFile):
    logging.info(f"Playing sound '{os.path.basename(wavFile)}'")
    return await asyncio.create_subprocess_exec('aplay', '-q', wavFile)


async def scan_qrcode_async(channel, event_time):  # need args, _ does not seem to work???

    logging.info('Photo sensor active, activating light and camera')
    aplay_scanning = await play_sound_start_async(SOUND_SCANNING)
    GPIO.output(PIN_LED, GPIO.HIGH)

    # scan QR code
    # zbarcam --quiet --nodisplay --raw -Sdisable -Sqrcode.enable --prescale=320x240 /dev/video0
    zbarcam = subprocess.Popen(['zbarcam', '--quiet', '--nodisplay', '--raw', '-Sdisable', '-Sqrcode.enable',
                                '--prescale=320x240', '/dev/video0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    poll_obj = select.poll()
    poll_obj.register(zbarcam.stdout, select.POLLIN)

    # wait for scan result (or timeout)
    start_time = time.time()
    poll_result = False
    while ((time.time() - start_time) < QR_SCANNER_TIMEOUT and (not poll_result)):
        poll_result = poll_obj.poll(100)
    if (poll_result):
        qr_code = zbarcam.stdout.readline().rstrip().decode("utf-8")

    # stop scanning
    zbarcam.terminate()
    GPIO.output(PIN_LED, GPIO.LOW)
    aplay_scanning.terminate()

    qr_valid = False
    if poll_result:
        logging.info(f"QR Code: {qr_code}")

        if qr_code.startswith("spotify:playlist:") or qr_code.startswith("spotify:album:"):
            await play_sound_start_async(SOUND_SCAN_OK)
            await qudiolib.player_start_context(context=qr_code)
            qr_valid = True
        else:
            logging.warning(f"Invalid QR Code: {qr_code}")

    else:
        logging.warning('Timeout on zbarcam')

    if not qr_valid:
        await play_sound_start_async(SOUND_SCAN_FAIL)

    # wait until sensor is not blocked anymore
    while GPIO.input(PIN_SENSOR) == GPIO.LOW:
        await asyncio.sleep(0.1)

    # delay a bit more to allow to withdraw card without re-triggering sensor
    await asyncio.sleep(QR_SCANNER_DELAY_AFTER)
