#!/usr/bin/env python3

import dbus

session_bus = dbus.SessionBus()
mplayer_proxy = session_bus.get_object('org.mpris.MediaPlayer2.spotifyd', '/org/mpris/MediaPlayer2')
mplayer_player = dbus.Interface(mplayer_proxy, 'org.mpris.MediaPlayer2.Player')

mplayer_player.OpenUri(dbus.Staring("spotify:playlist:37i9dQZF1DX7F6T2n2fegs"))
