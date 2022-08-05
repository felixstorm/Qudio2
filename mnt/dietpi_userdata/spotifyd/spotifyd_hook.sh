#!/bin/bash

mkdir -p /tmp/spotifyd

# need to write on 'change' and 'endoftrack' to overwrite position
# otherwise the display position will still show based on the play event from the track before
if ! [[ "load preload volumeset" =~ ${PLAYER_EVENT} ]]; then
    echo -e "${PLAYER_EVENT}\n${POSITION_MS}\n${DURATION_MS}" > /tmp/spotifyd/event
fi
