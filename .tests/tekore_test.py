#!/usr/bin/env python3

import tekore as tk

conf = tk.config_from_file('spotifyd.conf', 'tekore', return_refresh=True)
token = tk.refresh_user_token(*conf[:2], conf[3])

spotify = tk.Spotify(token)
devices = spotify.playback_devices()
device = next(x for x in devices if x.name.startswith('Spotifyd'))
print(device)
spotify.playback_start_context('spotify:playlist:37i9dQZF1DX7F6T2n2fegs', device_id=device.id)
