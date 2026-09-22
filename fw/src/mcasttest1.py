#!python3
"""
Quick test of multicast commands on micropython, esp32...

Karl: remember though, if you have wifi for multicast,  you have mqtt just right there already....
and in helloween2, you already have HA control of things....
"""


try:
    import secrets
except ImportError:
    print("no wifi config, run an AP mode I guess....")
    pass

import binascii
import machine
import network
import socket
import time

KMCAST_IP = "239.131.42.181"
KMCAST_PORT = 6273
KMCAST_IP_BIN = bytes(map(int, KMCAST_IP.split("."))) + bytes(4)

class Core:
    def __init__(self):
        self.uid_s = binascii.hexlify(machine.unique_id()).decode()
        # lol, mpy 1.17, that I had lying around is too old for that.
        self.nodeid = f"kgarden-{self.uid_s[:-4]}"

    def do_station(self):
        """ An alternate simple start, normally we let mqtt-as just take care of bizness"""
        network.hostname(self.nodeid)
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(False)  # reset interface
        self.sta.active(True)
        self.sta.connect(secrets.Wifi.SSID, secrets.Wifi.PASSWORD)

        att = 0
        while not self.sta.isconnected():
            time.sleep(1)
            att += 1
            txt = f"Trying: {secrets.Wifi.SSID}, #{att}"
            #self.tft.text(self.font8, txt, 0, 100, self.colour_status)
            print(txt)
            # Might be nice to even run a connection loop a few times,
            # offer an AP for x minutes, but retry again every now and again?
            # ie, offer a chance to have an AP to reconfigure, but still do the right thing if we're brought back
            # into range of the desired place?
        txt = f"Conn: {self.sta.ifconfig()[0]}"
        #self.tft.text(self.font8, txt, 0, 100, self.colour_status)
        print(txt)

def inet_aton(addr):
    ip_as_bytes = bytes(map(int, addr.split(".")))
    return ip_as_bytes


def start():
    c = Core()
    c.do_station()
    return c

def kthing():
    serv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # wot?
    #addr = socket.getaddrinfo("0.0.0.0", KMCAST_PORT, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
    serv_sock.bind(("0.0.0.0", KMCAST_PORT))
    serv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, KMCAST_IP_BIN)

    #REUSE_SOCKET = 0
    #if REUSE_SOCKET:
    #    resp_sock = serv_sock
    #else:
    #    resp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        print('Waiting for anything....')
        data, addr2 = serv_sock.recvfrom(1024)
        # looks like sockaddr isn't in old 1.21 in myu old trees
        #print("From: ", socket.sockaddr(addr2))
        print("From: ", addr2)
        print(data)