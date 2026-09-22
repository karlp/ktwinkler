#!python3
"""
Check that we're receiving anything at all....
Ok, this works, now let's make it so that ... we can do it with asyncio, so we can hook this together
with the twinkle hardware itself.
"""

import home
import machine
import struct

# Blocking call!
station = home.HomeStation("kartnet1")


import socket
# Define network and artnet parameters
PORT = 6454
UNIVERSE_TARGET = 0  # Change to the universe you want to listen to

# Set up UDP socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', PORT))

print("Listening for Art-Net data on port", PORT)

while True:
    data, addr = s.recvfrom(1024)
    if len(data) > 19:  # Basic check for Art-Net header
        if data[0:7] == b'Art-Net' and data[8] == 0x00:  # Art-Net ID and OpCode low byte for ArtDMX
            universe = data[14] | (data[15] << 8)
            print(f"Received packet from {addr}, Universe: {universe}")
            if universe == UNIVERSE_TARGET:
                dmx_data = data[18:]
                #print(f"Received Universe {universe} from {addr}, Channels: {len(dmx_data)}")
                # We configured two, two channel dimmers on channels 3-4 and 27-28
                # This live updates, so... we've got the basics in place now.
                twinkle1 = struct.unpack('BB', dmx_data[2:4])
                twinkle2 = struct.unpack('BB', dmx_data[26:28])
                print(f"DMX Data (hacked ):", twinkle1, twinkle2)
