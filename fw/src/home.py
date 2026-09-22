#!python3
"""
A basic stub that can connect to the "home" network (as a station!)
and drop you there, used to cut down on copypasta for testing ideas.
"""

import binascii
import machine
import network
import time

import secrets


class HomeStation:
    def __init__(self, host_prefix="khome"):
        self.station_id = f"{host_prefix}_{binascii.hexlify(machine.unique_id()).decode()}"
        self.do_station()

    def do_station(self):
        """
        Blocking, simple, just get me connected and give me back.
        """
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(False)  # reset interface
        self.sta.active(True)
        self.sta.connect(secrets.Wifi.SSID, secrets.Wifi.PASSWORD)

        att = 0
        while not self.sta.isconnected():
            att += 1
            txt = f"Trying: {secrets.Wifi.SSID}, #{att}"
            print(txt)
            time.sleep_ms(500)
        txt = f"Conn: {self.sta.ifconfig()[0]}"
        print(txt)
        