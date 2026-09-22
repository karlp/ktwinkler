import socket

KMCAST_IP = "239.131.42.181"
KMCAST_PORT = 6273

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
if hasattr(socket, "IP_MULTICAST_TTL"):
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 8)
for i in range(2):
    print(s.sendto(b'some data', (KMCAST_IP, KMCAST_PORT)))
s.close()
print('done')