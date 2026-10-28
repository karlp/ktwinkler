#!python3
"""
Still extremely simplistic artnet receiver, but with more asyncio,
connected to our asyncio twinkler
"""

import asyncio
import collections
import machine
import random
import select
import socket
import struct
import time

import home
import config_node
config = config_node.lookup_config()
import ptwinkler

# Blocking call! (TODO - use config_node for home device ids? nahh, no need to tie them together)
station = home.HomeStation("kartnet1")


class ArtNetOpcode:
    """Very incomplete"""
    Poll = 0x2000
    PollReply = 0x2100
    Output = 0x5000
    Dmx = 0x5000



class ADumbArtnetTwinklerPhased:
    """
    An equally dumb twinkler handler, just takes care of converting the dmx into logical for the twinkler instance.
    """
    def __init__(self, pt: ptwinkler.TwinklPhased):
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

    async def process_packet_real(self, count, saddr):
        if count < 14:
            return
        data = self.buffer[:count]
        if data[0:7] != b'Art-Net':
            return

        # note... little...
        opcode, = struct.unpack_from("<H", data[8:10])
        print(f"opcode received is: {opcode:x}")

        if opcode == ArtNetOpcode.Poll:
            #lol, big ;)
            # TODO - for every byte short from 14..22, fill in zeros if it didn't arrive.
            proto, flags, diag = struct.unpack_from(">HBB", data[10:14])
            # I think they just want us to reply here?
            print(f"attempting to reply to poll: proto: {proto:x}, flags: {flags:x}, diag: {diag:x}")
            # FIXME - we should really defer to a processing task, rather than building here?
            # is it ok yto just build, then defer the post with an async task? probably....
            # time.sleep(random(.. something less than one second))
            #packet = b'Art-Net\x00' + ... the rest of it...
            # fucking, byteswap our IP... fucking.. wot. but ok. thanks artnet.
            #ip_rev = 0xaabbccdd #station.sta.ipconfig("addr4")[0] # fucking fuck
            ip_rev = 0
            for i, octet in enumerate(station.sta.ipconfig("addr4")[0].split('.')):
                #ip_rev = (ip_rev << 8) | int(octet)
                ip_rev |= int(octet) << (i * 8)
            version = 2022
            netswitch = 0 # I think these are interesting, but not for me
            subswitch = 0
            oem = 0xcafe
            ubea = 0
            status1 = 0xf0 # indicators normal, no ubea, no RDM, port address programming unused
            esta = 0xf00d
            #node_report = "#0000 [6969] lol"
            node_report = ""
            #num_ports = 0 # "nodes can ignore this, it's implicit from portytpes...."
            num_ports = 1  # maybe they really want it?
            #port_types = 0x80808080 # output only, I think?
            port_types = 0x80000000 # just one output port
            #good_input = 0x01010101 # ? maybe? (or 80808080?)
            good_input = 0x80000000 # ? maybe? (or 80808080?)
            good_output = 0x80000000 # otuputing dmx, we're a plain real node...
            swin = 0 # fuck this addressing complication, I want to try out discovery! FIXME
            swout = 0 # fuck this addressing complication, I want to try out discovery! FIXME
            style = 0
            mac_h32 = 0
            mac_l16 = 0
            # This is not going to be the most performant, but it's tedious doing the size offsetting
            packet = bytearray()
            # lol, no whitespace allowed in fmt strings in mpy
            packet.extend(struct.pack("<8sHLH", b"Art-Net", ArtNetOpcode.PollReply, ip_rev, 0x1936))
            packet.extend(struct.pack(">HBBHBB", version, netswitch, subswitch, oem, ubea, status1))
            packet.extend(struct.pack("<H", esta))
            packet.extend(struct.pack("<18s64s64s", "ktwinkler", f"esp32node_{config.device_uid}", node_report))
            packet.extend(struct.pack(">HLLLLL", num_ports, port_types, good_input, good_output, swin, swout))
            # priotity, macro, remote, 3xspare, all zero.
            packet.extend(struct.pack(">BBBBBBBLH", 0, 0, 0, 0,0,0, style, mac_h32, mac_l16))
            
            #packet = struct.pack()
            async def _artnetpoll_reply(s: socket.socket, daddr: socket.AddressInfo, pkt: bytes):
                """Send pkt to daddr on s, after an artnet random delay"""
                await asyncio.sleep_ms(random.randint(50, 1000))
                x = s.sendto(pkt, daddr)
                print(f"sent a reply to {daddr} and got {x}")

            asyncio.create_task(_artnetpoll_reply(self.sock, saddr, packet))
            return

        if opcode == ArtNetOpcode.Dmx:
            if len(data) > 19:  # Basic check for enough of an output package
                universe = data[14] | (data[15] << 8)
                print(f"Received packet for Universe: {universe}")
                if universe == self.universe_target:
                    dmx_data = data[18:]
                    #print(f"Received Universe {universe}, Channels: {len(dmx_data)}")
                    for start_chan in self.handlers:
                        start_chan, length, handler = self.handlers[start_chan]
                        print(f"Processing dmx data for channel: {start_chan}/{length}")
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

        async def _same_network_handler_really(self: ADumbArtnet):
            tx = time.ticks_us()
            #count = self.sock.readinto(self.buffer)
            self.buffer, addr = self.sock.recvfrom(1024)
            if not self.buffer:
                return
            count = len(self.buffer)
            if not count:
                return
            self.sock_stats.append(time.ticks_diff(time.ticks_us(), tx))
            t1 = time.ticks_us()
            #await self.process_packet(self.buffer[:count])
            await self.process_packet_real(count, addr)
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
    #asyncio.create_task(artnet.monitor_stats())
    artnet.add_handler(config.artnet_channel + 0, 2, ADumbArtnetTwinklerPhased(ptwinkler.TwinklPhased(machine.Pin.board.PWM1, machine.Pin.board.PWM2)))
    artnet.add_handler(config.artnet_channel + 2, 2, ADumbArtnetTwinklerPhased(ptwinkler.TwinklPhased(machine.Pin.board.PWM3, machine.Pin.board.PWM4)))
    artnet.add_handler(config.artnet_channel + 4, 2, ADumbArtnetTwinklerPhased(ptwinkler.TwinklPhased(machine.Pin.board.PWM5, machine.Pin.board.PWM6)))
    # loll., out of pwm channels.
    #artnet.add_handler(12, 2, ADumbArtnetTwinklerPhased(ptwinkler.TwinklPhased(machine.Pin.board.PWM7, machine.Pin.board.PWM8)))
    while True:
        await asyncio.sleep(3)
        print("tick")

def main():
    asyncio.run(task_main())

#if __name__ == "__main__":
#    main()
#main()


# TODO:
# before you vibe code this in C, try and do normal blocking reads, (no twinkler)
# and then also do the classic poll nonblockign on the socket,
# we might need to have the poll be a top level and await that way maybe?
# it's definitely not right like this, no way.