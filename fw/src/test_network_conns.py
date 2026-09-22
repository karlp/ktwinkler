#!python3
"""
Test main to explore whether these boards can see wifi from the house
as is, or whether we need more.
"""

import binascii
import machine
import network
import socket
import time

import secrets
import twinkler


def check_host(ip, port=80):
    try:
        # Get address info and attempt a TCP connection
        addr = socket.getaddrinfo(ip, port)[0][-1]
        s = socket.socket()
        s.settimeout(1)
        s.connect(addr)
        s.close()
        return True
    except Exception:
        return False

class Core:
    def __init__(self):
        self.uid_s = binascii.hexlify(machine.unique_id()).decode()
        self.t = twinkler.Twinkl(machine.Pin.board.PWM1, machine.Pin.board.PWM2)

    def do_station(self):
        """ An alternate simple start, normally we let mqtt-as just take care of bizness"""
        network.hostname(f"kgarden-{self.uid_s[:-4]}")
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(False)  # reset interface
        self.sta.active(True)
        self.sta.connect(secrets.Wifi.SSID, secrets.Wifi.PASSWORD)

        att = 0
        while not self.sta.isconnected():
            # twinkle colour A to indicate attempts...
            # (TODO - make twinkling an asyncio, instead of busy spinning ;)
            self.t.twinkle(0)
            att += 1
            txt = f"Trying: {secrets.Wifi.SSID}, #{att}"
            print(txt)
        txt = f"Conn: {self.sta.ifconfig()[0]}"
        print(txt)

    def do_idle(self):
        """ Idle loop, just twinkle slowly """
        while True:
            if check_host("192.168.88.20", 8080):
                self.t.twinkle(1)
                time.sleep(1)
            else:
                #reboot and try again?
                machine.reset()

c = Core()
c.do_station()
c.do_idle()
