#!python3
"""
Still extremely simplistic artnet receiver, but with more asyncio,
connected to our asyncio twinkler
"""

import asyncio
import collections
import machine
import select
import socket
import struct
import time

import home
import config_node
config = config_node.lookup_config()
import atwinkler
import ptwinkler

# Blocking call! (TODO - use config_node for home device ids? nahh, no need to tie them together)
station = home.HomeStation("kartnet1")

class ADumbArtnetTwinklerx1:
    """
    A single (bi) channel twinkler, connected to artnet.
    very very alpha concept of what a useful api here should be.
    """
    def __init__(self, atwinkler: atwinkler.TwinklAsync, start_chan):
        self.start_chan = start_chan
        self.len = 2
        self._at = atwinkler
        # connect this "logical device's" maintennance task to the event loop
        asyncio.create_task(self._at.task_maintain_logical())

    def handle_dmx(self, dmx_data):
        """We're defining that this handler gets _just_ it's own channels"""
        aa, bb = struct.unpack('BB', dmx_data[:self.len])
        #print(f"{self} Handling DMX data: {aa}, {bb}")
        self._at.set_logical([aa, bb])

    def __repr__(self):
        return f"<ADumbArtnetTwinklerx1 start_chan={self.start_chan} len={self.len}>"

class ADumbArtnetTwinklerPhased:
    """
    An equally dumb twinkler handler, just takes care of converting the dmx into logical for the twinkler instance.
    """
    def __init__(self, pt: ptwinkler.TwinklPhased, start_chan):
        self.start_chan = start_chan
        self.len = 2
        self.t = pt

    def handle_dmx(self, dmx_data):
        """We're defining that this handler gets _just_ it's own channels"""
        aa, bb = struct.unpack('BB', dmx_data[:self.len])
        #print(f"{self} Handling DMX data: {aa}, {bb}")
        # dmx is 0..255, we're doing 0..1023, so just.. x4?
        self.t.set_logical([aa*4, bb*4])

class ADumbArtnet:
    def __init__(self, universe_target, bind='0.0.0.0', port=6454):
        self.universe_target = universe_target
        self.bind = bind
        self.port = port
        # We're going to need.... some sort of dispatching...
        # and we probably don't want a network instance for each potential node?
        self.handlers = {}
        self.process_stats = collections.deque([], 100)
        self.sock_stats = collections.deque([], 100)
        self.buffer = bytearray(1024)

    def add_handler(self, start_chan, length, handler):
        self.handlers[start_chan] = (start_chan, length, handler)


    async def process_packet(self, count):
        for start_chan in self.handlers:
            start_chan, length, handler = self.handlers[start_chan]
            await handler.handle_dmx(b"fk")

    async def process_packet_real(self, count):
        data = self.buffer[:count]
        if len(data) > 19:  # Basic check for Art-Net header
            if data[0:7] == b'Art-Net' and data[8] == 0x00:  # Art-Net ID and OpCode low byte for ArtDMX
                universe = data[14] | (data[15] << 8)
                #print(f"Received packet for Universe: {universe}")
                if universe == self.universe_target:
                    dmx_data = data[18:]
                    #print(f"Received Universe {universe} from {addr}, Channels: {len(dmx_data)}")
                    # We configured two, two channel dimmers on channels 3-4 and 27-28
                    # This live updates, so... we've got the basics in place now.
                    # TODO - look at our handlers and dispatch them...
                    # twinkle1 = struct.unpack('BB', dmx_data[2:4])
                    # twinkle2 = struct.unpack('BB', dmx_data[26:28])
                    # print(f"DMX Data (hacked ):", twinkle1, twinkle2)
                    for start_chan in self.handlers:
                        start_chan, length, handler = self.handlers[start_chan]
                        handler.handle_dmx(dmx_data[start_chan-1:start_chan-1+length])

    async def monitor_stats(self):
        def make_stats(data):
            s = sorted(data)
            if len(s) % 2 != 0:
                median = s[len(s) // 2]
            else:
                median = (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
            mean = sum(data) / len(data)
            lower_quartile = s[len(s) // 4]
            return median, mean, lower_quartile
        while True:
            await asyncio.sleep_ms(1000)
            # snapshot copy to do stats
            if len(self.process_stats) < 2:
                continue
            tlist = list(self.process_stats)
            median, mean, lower_quartile = make_stats(tlist)
            print(f"Process timing {len(tlist)}: median: {median} mean: {mean} lq {lower_quartile}")
            tlist = list(self.sock_stats)
            median, mean, lower_quartile = make_stats(tlist)
            print(f"SOCK rx {len(tlist)}: median: {median} mean: {mean} lq {lower_quartile}")


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


        async def _network_work1(self):
            # readinto is "performant" but we lose the source address information?
            tx = time.ticks_us()
            count = self.sock.readinto(self.buffer)
            if not count:
                return
            self.sock_stats.append(time.ticks_diff(time.ticks_us(), tx))
            t1 = time.ticks_us()
            #await self.process_packet(self.buffer[:count])
            #await self.process_packet(count)
            #print(f"processed {count} bytes lol")
            self.process_stats.append(time.ticks_diff(time.ticks_us(), t1))


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

    async def task_network_via_poll(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.bind, self.port))

        poller = select.poll()
        poller.register(self.sock, select.POLLIN)

        async def _same_network_handler_really(self):
            tx = time.ticks_us()
            #count = self.sock.readinto(self.buffer)
            self.buffer = self.sock.recv(1024)
            if not self.buffer:
                return
            count = len(self.buffer)
            if not count:
                return
            self.sock_stats.append(time.ticks_diff(time.ticks_us(), tx))
            t1 = time.ticks_us()
            #await self.process_packet(self.buffer[:count])
            await self.process_packet_real(count)
            print(f"processed {count} bytes lol")
            self.process_stats.append(time.ticks_diff(time.ticks_us(), t1))


        while True:
            events = poller.poll(0)
            if not events:
                await asyncio.sleep_ms(5)
                continue
            for fd, flag in events:
                if flag & select.POLLIN:
                    await _same_network_handler_really(self)




async def task_main():
    async def task_dummy_idle():
        i = 1
        while True:
            await asyncio.sleep_ms(650)
            i += 1
            print(f"Dummy idle tick {i}")

    artnet = ADumbArtnet(universe_target=0, port=6454)
    #asyncio.create_task(artnet.task_network())
    asyncio.create_task(artnet.task_network_via_poll())
    asyncio.create_task(artnet.monitor_stats())
    # well, if even _one_ async flickers, lets try moving to poll then? 
    #atwinkler_instance1 = atwinkler.TwinklAsync(machine.Pin.board.PWM1, machine.Pin.board.PWM2, async_step_ms=2)
    h1 = ptwinkler.TwinklPhased(machine.Pin.board.PWM1, machine.Pin.board.PWM2)
    h2 = ptwinkler.TwinklPhased(machine.Pin.board.PWM3, machine.Pin.board.PWM4)
    #atwinkler_instance2 = atwinkler.TwinklAsync(machine.Pin(32), machine.Pin(33))
    artnet.add_handler(3, 2, ADumbArtnetTwinklerPhased(h1, 3))
    artnet.add_handler(27, 2, ADumbArtnetTwinklerPhased(h2, 27))
    #artnet.add_handler(3, 2, ADumbArtnetTwinklerx1(atwinkler_instance1, 3))
    #artnet.add_handler(27, 2, ADumbArtnetTwinklerx1(atwinkler_instance2, 27))
    while True:
        await asyncio.sleep(3)
        print("tick")

def main():
    asyncio.run(task_main())

#if __name__ == "__main__":
#    main()
main()


# TODO:
# before you vibe code this in C, try and do normal blocking reads, (no twinkler)
# and then also do the classic poll nonblockign on the socket,
# we might need to have the poll be a top level and await that way maybe?
# it's definitely not right like this, no way.