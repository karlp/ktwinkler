#!python3
"""
A "stripped down" UDP receive performance test for MicroPython.
Tries a few different ways of doing non-blocking UDP receive, though, 
for these tests, there's nothing _else_
Should run on any micropython with wifi station mode...

You can run this like so:
```
mpremote exec "mode='poll_register'; ssid='some_ssid'; password='some_password'" run src/test_udp_rx_perf.py
```

Modes that can be chosen:
- poll_register: use select.poll() and register the socket for events
- sockopt20: use socket option 20 for event-driven receive
- async_poll: use asyncio with poll for non-blocking receive
- async_simple: use simple asyncio for non-blocking receive

Timings for receiving 900byte udp packets, broadcast every 50 ms.
(timings _are_ faster with small packets, but they are not the underlying problem)
Packets can be generarted with the ht_send_udp.py script here.

On ESP32-C3...
~80 usecs - ../fw-alts/test-udp-rx-perf (ESP-IDF C based)
~630 usecs for mode poll_register
~700 usecs for mode sockopt20
~630 usecs for mode async_poll
~900 usecs for mode async_simple
"""

import asyncio
import collections
import network
import select
import socket
import sys
import time

# You can set this here, or pass them as args to main()
try:
    DEFAULT_SSID = ssid
    DEFAULT_PASSWORD = password
except:
    print("ssid and password not provided by mpremote exec, using default values (See help)")
    DEFAULT_SSID = "your_default_ssid"
    DEFAULT_PASSWORD = "your_default_password"


def do_station(ssid, password):
    """
    Blocking, simple, just get me connected and give me back.
    """
    sta = network.WLAN(network.STA_IF)
    sta.active(False)  # reset interface
    sta.active(True)
    sta.connect(ssid, password)

    att = 0
    while not sta.isconnected():
        att += 1
        print(f"Trying SSID: {ssid}, #{att}")
        time.sleep_ms(500)
    print(f"Conn: {sta.ifconfig()[0]}")

class TestUdpRxPerf:
    def __init__(self, bind='0.0.0.0', port=5005):
        self.bind = bind
        self.port = port
        self.sock_stats = collections.deque([], 100)
        self.buffer = bytearray(1024)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def make_stats(self, data):
        """Simple, veryyyyy basic stats"""
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

    def _sock20_handle_sock_evts(self, s):
        t1 = time.ticks_us()
        data = self.sock.recv(1024)
        if not data:
            print("No data received, but got a socket event?!")
            return
        self.sock_stats.append(time.ticks_diff(time.ticks_us(), t1))
        #print(f"rx len: {len(data)}")

    def run_sockopt20(self):
        """Main synchronous run method for using socket option 20"""
        self.sock.setsockopt(socket.SOL_SOCKET, 20, self._sock20_handle_sock_evts)
        self.sock.bind((self.bind, self.port))

        tick_stats = time.ticks_ms()
        # while True:
        #     # will also try with asyncio here?
        #     time.sleep(1)

        poller = select.poll()
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


    def run_poll_register(self):
        """Main synchronous run method for using poll and registering the socket for events."""
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
                            print("For tcp, this is conn closed, for UDP, should never happen")
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

    async def _async_network_work(self):
        tx = time.ticks_us()
        #count = self.sock.readinto(self.buffer)
        self.buffer = self.sock.recv(1024)
        if not self.buffer:
            return
        count = len(self.buffer)
        if not count:
            return
        self.sock_stats.append(time.ticks_diff(time.ticks_us(), tx))


    async def task_async_simple(self):
        """
        Simplistic asyncio task, first iteration.
        """ 
        self.sock.bind((self.bind, self.port))

        while True:
            try:
                await self._async_network_work()
            except OSError as e:
                if e.errno == 11:  # EAGAIN, no data available
                    await asyncio.sleep_ms(20)
                else:
                    raise
            # Yes, this is polling every 20 ms So it _should_ just be less efficient,
            # it shouldn't be significantly _slower_ as well, IMO...
            await asyncio.sleep_ms(20)


    async def task_async_poll(self):
        """asyncio, but attempting to register the socket onto poller above..."""
        self.sock.bind((self.bind, self.port))

        poller = select.poll()
        poller.register(self.sock, select.POLLIN)

        while True:
            events = poller.poll(0)
            if not events:
                await asyncio.sleep_ms(5)
                continue
            for fd, flag in events:
                if flag & select.POLLIN:
                    await self._async_network_work()


    async def monitor_stats_async(self):
        while True:
            await asyncio.sleep_ms(1000)
            median, mean, lower_quartile = self.make_stats(self.sock_stats)
            print(f"SOCK rx {len(self.sock_stats)}: median: {median} mean: {mean} lq {lower_quartile}")


    async def run_async(self, mode):
        if mode == "async_simple":
            asyncio.create_task(self.task_async_simple())
        elif mode == "async_poll":
            asyncio.create_task(self.task_async_poll())
        else:
            raise ValueError(f"Unknown async mode: {mode}")
        asyncio.create_task(self.monitor_stats_async())
        while True:
            # "do nothing"
            await asyncio.sleep(3)



def main(mode, ssid=DEFAULT_SSID, password=DEFAULT_PASSWORD):
    do_station(ssid, password)
    test = TestUdpRxPerf(bind="0.0.0.0", port=5005)
    if mode == "sockopt20":
        test.run_sockopt20()
    elif mode == "poll_register":
        test.run_poll_register()
    elif mode in ["async_simple", "async_poll"]:
        asyncio.run(test.run_async(mode))
    else:
        print(f"Unknown mode: {mode}")


if __name__ == "__main__":
    print("Running on: ", sys.implementation)
    main(mode)

