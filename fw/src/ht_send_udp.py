#!python3
"""
Hack host test to see how packet size affects micropython rx performance.
"""
import argparse
import random
import socket
import time

UDP_IP = "192.168.88.255"  # Target IP address (localhost)
UDP_PORT = 5005        # Target port number
PACKET_LENGTH = 900
INTER_PACKET_DELAY = 0.05


def main():
    parser = argparse.ArgumentParser(description="Send random UDP broadcast packets.")
    parser.add_argument("--ip", default=UDP_IP, help=f"Destination IP (default: {UDP_IP})")
    parser.add_argument("--port", type=int, default=UDP_PORT,
                        help=f"Destination UDP port (default: {UDP_PORT})")
    parser.add_argument("--packet-length", type=int, default=PACKET_LENGTH,
                        help=f"Packet payload length in bytes (default: {PACKET_LENGTH})")
    parser.add_argument("--inter-packet-delay", type=float, default=INTER_PACKET_DELAY,
                        help=f"Delay between packets in seconds (default: {INTER_PACKET_DELAY})")
    args = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            message = random.randbytes(args.packet_length)
            sock.sendto(message, (args.ip, args.port))
            time.sleep(args.inter_packet_delay)


if __name__ == "__main__":
    main()


