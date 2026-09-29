#!python3
"""
Based on our artnet demo, but stripped down while we try and figure out
how to receive udp packets without blocking things unduly.

all of these are timings for receiving 900byte udp packets, broadcast every 50ms

~80 usecs - ../fw-alts/test-udp-rx-perf (ESP-IDF C based)
~650 usecs for using poller directly - this file, test.run()
~720 usecs for socket option 20 - this file. test.run_sockopt20()
~850 usecs for async via poll  - test_artnet1_async, test.task_network_via_poll())
~900 usecs for original simplistic asyncio - test_artnet1_async, test.task_network()

"""

import asyncio
import collections
import machine
import select
import socket
import struct
import time

###### THIS SECTION IS JUST MY NETWORK CONFIG
import home
import config_node
config = config_node.lookup_config()

# Blocking call! (TODO - use config_node for home device ids? nahh, no need to tie them together)
station = home.HomeStation("kartnet1")
###### ^^^^  DOWN TO HERE.

class SyncDumbArtnet:
    def __init__(self, universe_target, bind='0.0.0.0', port=6454):
        self.universe_target = universe_target
        self.bind = bind
        self.port = port
        self.sock_stats = collections.deque([], 100)
        self.buffer = bytearray(1024)

    def make_stats(self, data):
        if len(data) == 0:
            return 0, 0, 0
        s = sorted(data)
        if len(s) % 2 != 0:
            median = s[len(s) // 2]
        else:
            median = (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
        mean = sum(data) / len(data)
        lower_quartile = s[len(s) // 4]
        return median, mean, lower_quartile

    def handle_sock_evts(self, a):
        t1 = time.ticks_us()
        data = self.sock.recv(1024)
        if not data:
            print("No data received, but got a socket event?!")
            return
        self.sock_stats.append(time.ticks_diff(time.ticks_us(), t1))
        #print(f"rx len: {len(data)}")


    def run_sockopt20(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, 20, self.handle_sock_evts)
        self.sock.bind((self.bind, self.port))

        #while True:
        #    # will also try with asyncio here?
        #    time.sleep(1)

        poller = select.poll()
        tick_stats = time.ticks_ms()
        while True:
            events = poller.poll(1000)
            for fd, flag in events:
                print("Unexpected, we didn't register for anything?!")
                if flag & select.POLLIN:
                    print("VERY Unexpected, we didn't register for anything?!")
            if time.ticks_diff(time.ticks_ms(), tick_stats) > 1000:
                tick_stats = time.ticks_ms()
                median, mean, lower_quartile = self.make_stats(self.sock_stats)
                print(f"SOCK rx {len(self.sock_stats)}: median: {median} mean: {mean} lq {lower_quartile}")
            


    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.bind, self.port))

        poller = select.poll()
        poller.register(self.sock, select.POLLIN)

        tick_stats = time.ticks_ms()
        while True:
            events = poller.poll(1000)
            for fd, flag in events:
                # Check if the flag indicates incoming data is available
                if flag & select.POLLIN:
                    try:
                        t1 = time.ticks_us()
                        data = self.sock.recv(1024)
                        self.sock_stats.append(time.ticks_diff(time.ticks_us(), t1))
                        if not data:
                            # Connection closed by the remote host
                            print("Connection closed by peer.")
                            break
                            
                        #print(f"rx len: {len(data)}")
                        
                    except OSError as e:
                        # Handle unexpected socket errors
                        print("Socket error:", e)
                        break

            if time.ticks_diff(time.ticks_ms(), tick_stats) > 1000:
                tick_stats = time.ticks_ms()
                median, mean, lower_quartile = self.make_stats(self.sock_stats)
                print(f"SOCK rx {len(self.sock_stats)}: median: {median} mean: {mean} lq {lower_quartile}")
            #print("tick lmain poll")


async def task_main():
    artnet = ADumbArtnet(universe_target=0, port=5005)
    asyncio.create_task(artnet.task_network_via_poll())
    asyncio.create_task(artnet.monitor_stats())
    while True:
        await asyncio.sleep(3)
        print("tick")

def main():
    test = SyncDumbArtnet(universe_target=0, port=5005)
    #test.run()
    test.run_sockopt20()


#if __name__ == "__main__":
#    main()
main()


# TODO:
# TODO - toss all the artnet, just make a swallowing udp receiver, with all versions, and args to choose from
