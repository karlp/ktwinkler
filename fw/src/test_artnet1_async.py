#!python3
"""
Still extremely simplistic artnet receiver, but with more asyncio,
connected to our asyncio twinkler
"""

import asyncio
import machine
import socket
import struct

import home
import config_node
config = config_node.lookup_config()
import atwinkler

# Blocking call! (TODO - use config_node for home device ids? nahh, no need to tie them together)
station = home.HomeStation("kartnet1")

class ADumbArtnetTwinklerx1:
    """
    A single (bi) channel twinkler, connected to artnet.
    very very alpha concept of what a useful api here should be.
    """
    def __init__(self, atwinkler: atwinkler.ATwinkler, start_chan):
        self.start_chan = start_chan
        self.len = 2
        self._at = atwinkler
        # connect this "logical device's" maintennance task to the event loop
        asyncio.create_task(self._at.task_maintain_logical())

    def handle_dmx(self, dmx_data):
        """We're defining that this handler gets _just_ it's own channels"""
        aa, bb = struct.unpack('BB', dmx_data[:self.len])
        print(f"{self} Handling DMX data: {aa}, {bb}")
        self._at.logical = [aa, bb]

    def __repr__(self):
        return f"<ADumbArtnetTwinklerx1 start_chan={self.start_chan} len={self.len}>"

class ADumbArtnet:
    def __init__(self, universe_target, bind='0.0.0.0', port=6454):
        self.universe_target = universe_target
        self.bind = bind
        self.port = port
        # We're going to need.... some sort of dispatching...
        # and we probably don't want a network instance for each potential node?
        self.handlers = {}

    def add_handler(self, start_chan, length, handler):
        self.handlers[start_chan] = (start_chan, length, handler)


    async def process_packet(self, data):
        if len(data) > 19:  # Basic check for Art-Net header
            if data[0:7] == b'Art-Net' and data[8] == 0x00:  # Art-Net ID and OpCode low byte for ArtDMX
                universe = data[14] | (data[15] << 8)
                print(f"Received packet for Universe: {universe}")
                if universe == self.universe_target:
                    dmx_data = data[18:]
                    #print(f"Received Universe {universe} from {addr}, Channels: {len(dmx_data)}")
                    # We configured two, two channel dimmers on channels 3-4 and 27-28
                    # This live updates, so... we've got the basics in place now.
                    # TODO - look at our handlers and dispatch them...
                    twinkle1 = struct.unpack('BB', dmx_data[2:4])
                    twinkle2 = struct.unpack('BB', dmx_data[26:28])
                    print(f"DMX Data (hacked ):", twinkle1, twinkle2)
                    for start_chan in self.handlers:
                        start_chan, length, handler = self.handlers[start_chan]
                        handler.handle_dmx(dmx_data[start_chan-1:start_chan-1+length])


    async def task_network(self):
        """
        You _must_ run this task in the asyncio event loop to maintain the 
        network
        TODO - this can probably use poll instead maybe?
        """ 
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.bind, self.port))

        buffer = bytearray(1024)

        async def _network_work1(self):
            # readinto is "performant" but we lose the source address information?
            count = self.sock.readinto(buffer)
            if not count:
                return
            await self.process_packet(buffer[:count])


        while True:
            try:
                await _network_work1(self)
            except OSError as e:
                if e.errno == 11:  # EAGAIN, no data available
                    await asyncio.sleep_ms(20)
                else:
                    raise
            # we really do want to be able to respond fairly promptly here, so 
            # that we can do "smooth" ramps and so on...
            #
            # TODO - try and use poll to leave more time for the twinkler maintainer tasks..
            await asyncio.sleep_ms(20)

async def task_main():
    async def task_dummy_idle():
        i = 1
        while True:
            await asyncio.sleep_ms(650)
            i += 1
            print(f"Dummy idle tick {i}")

    artnet = ADumbArtnet(universe_target=0)
    asyncio.create_task(artnet.task_network())
    asyncio.create_task(task_dummy_idle())
    atwinkler_instance1 = atwinkler.TwinklAsync(machine.Pin.board.PWM1, machine.Pin.board.PWM2)
    atwinkler_instance2 = atwinkler.TwinklAsync(machine.Pin(2), machine.Pin(8))
    artnet.add_handler(3, 2, ADumbArtnetTwinklerx1(atwinkler_instance1, 3))
    artnet.add_handler(27, 2, ADumbArtnetTwinklerx1(atwinkler_instance2, 27))
    while True:
        await asyncio.sleep(3)
        print("tick")

def main():
    asyncio.run(task_main())

#if __name__ == "__main__":
#    main()
main()
