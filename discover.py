#!/usr/bin/env python

"""
Discover ADDP devices on the local network
"""

import sys
import socket
import struct
from pprint import pprint

from addp import build_request, parse_frame

def send_discovery():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        # you can only use the REUSE options OR the bind, not both
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
                pass
        
        sock.bind(("", 2362))
        mreq = struct.pack("4sl", socket.inet_aton('224.0.5.128'), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(1.0)
        msg = build_request(0x01, mac=(255,255,255,255,255,255))

        sock.sendto(msg, ("224.0.5.128", 2362))

        responses = []
        while True:
                try:
                        data, addr = sock.recvfrom(2048)
                        print(data.hex())
                except:
                        break

                if data is None or data == '':
                        break

                info = parse_frame(data)
                if info:
                        info['addp_ip'] = addr[0]
                        responses.append(info)

        sock.close()
        return responses

if __name__ == '__main__':
        sys.stderr.write('Sending discover message...\n')
        pprint(send_discovery())

