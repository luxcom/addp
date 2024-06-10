#!/usr/bin/env python

"""
Advanced Device Discovery Protocol (ADDP)

http://www.digi.com/wiki/developer/index.php/Advanced_Device_Discovery_Protocol_(ADDP)

Almost all info for this module comes from:
  http://qbeukes.blogspot.com/2009/11/advanced-digi-discovery-protocol_21.html
"""

import struct

typ_codes = {
        0x0001: "Discovery Request",
        0x0002: "Discovery Response",
        0x0003: "Static Network Configuration Request",
        0x0004: "Static Network Configuration Response",
        0x0005: "Reboot Request",
        0x0006: "Reboot Response",
        0x0007: "DHCP Network Configuration Request",
        0x0008: "DHCP Network Configuration Response"}

# {code: (desc, encoder, decoder)}
fld_codes = {
        0x01: ("MAC address", lambda x: struct.pack("6B", *x), lambda x: struct.unpack("6B", x)),
        0x02: ("IP address", lambda x: struct.pack("4B", *x), lambda x: struct.unpack("4B", x)),
        0x03: ("Netmask", lambda x: struct.pack("4B", *x), lambda x: struct.unpack("4B", x)),
        0x04: ("Network Name", lambda x: x, lambda x: x),
        0x05: ("Domain", lambda x: x, lambda x: x),
        0x06: ("HW Type", lambda x: struct.pack("B", x), lambda x: struct.unpack("B", x)[0]),
        0x07: ("HW Revision", lambda x: struct.pack("B", x), lambda x: struct.unpack("B", x)[0]),
        0x08: ("Firmware", lambda x: x, lambda x: x),
        0x09: ("Result message", lambda x: x, lambda x: x),
        0x0a: ("Result flag", lambda x: struct.pack("B", x), lambda x: struct.unpack("B", x)[0]),
        0x0b: ("IP Gateway", lambda x: struct.pack("BBBB", *x), lambda x: struct.unpack("BBBB", x)),
        0x0c: ("Configuration error code", lambda x: struct.pack(">H", x), lambda x: struct.unpack('>H', x)[0]),
        0x0d: ("device name", lambda x: x, lambda x: x),
        0x0e: ("Real Port number", lambda x: struct.pack(">L", x), lambda x: struct.unpack('>L', x)[0]),
        0x0f: ("DNS IP address", lambda x: struct.pack("BBBB", *x), lambda x: struct.unpack("BBBB", x)),
        0x10: ("UNKNOWN16", lambda x: struct.pack("BBBB", *x), lambda x: code_16_parser(x)),
        0x11: ("Error code", lambda x: struct.pack("B", x), lambda x: error_codes[ord(x)]),
        0x12: ("Serial Port Count", lambda x: struct.pack("B", x), lambda x: struct.unpack("B", x)[0]),
        0x13: ("Encrypted Real Port number", lambda x: struct.pack(">L", x), lambda x: struct.unpack('>L', x)[0]),
        0x14: ("ADDP Version", lambda x: struct.pack("BB", x), lambda x: struct.unpack('BB', x)[0]),
        0x19: ("UNKNOWN19", lambda x: struct.pack("B", x), lambda x: struct.unpack("B", x)[0]),
        0x1a: ("Device-ID", lambda x: x, lambda x: "%08X-%08X-%08X-%08X"%struct.unpack('>4L', x))}

error_codes = {
        0x00: "Success",
        0x01: "Authentication Failure",
        0x03: "Invalid Value",
        0x06: "Unable to save value"}

def build_frame(typ, body):
        return b"DIGI" + struct.pack('>HH', typ, len(body)) + body

def build_fields(flds):
        body = ""
        for c, v in list(flds.items()):
                val = fld_codes[c][1](v)
                body += struct.pack("BB", c, len(val)) + val
        return body

def parse_frame(d):
        info = {}
        if d[:4] != b'DIGI':    
            print('Invalid magic header:', repr(d[:4])) 
            return None 

        hdr = d[4:8]
        bdy = d[8:]
        (typ, ln) = struct.unpack(">HH", hdr)

        if len(bdy) != ln:
                print('Invalid format: lengths did not match:')
                print('expected: %d, got: %d' % (ln, len(bdy)))
                print(repr(d))
                return None

        if typ not in typ_codes:
                print('Unknown message code:', typ)
                return None

        info['code'] = typ
        info['msg_len'] = ln
        info['message'] = typ_codes[typ]
        info['msg_type'] = 'request'

        if typ == 0x01:
                # discovery req
                info['mac'] = struct.unpack("BBBBBB", bdy)

        elif typ == 0x03:
                # change ip req
                info['ip_addr'] = struct.unpack("BBBB", bdy[:4])
                info['subnet'] = struct.unpack("BBBB", bdy[4:8])
                info['gatway'] = struct.unpack("BBBB", bdy[8:12])
                info['mac'] = struct.unpack("BBBBBB", bdy[12:18])
                info['auth'] = bdy[18:]

        elif typ == 0x05:
                # reboot req
                info['mac'] = struct.unpack("BBBBBB", bdy[:6])
                info['auth'] = bdy[6:]

        elif typ == 0x07:
                # dhcp req
                #info['byte'] = struct.unpack("B", bdy[:1])
                info['mac'] = struct.unpack("BBBBBB", bdy[1:7])
                info['auth'] = bdy[7:]

        elif typ in [0x02, 0x04, 0x06, 0x08]:
                info['msg_type'] = 'response'
                vals = parse_response(bdy)
                info = dict(list(info.items()) + list(vals.items()))

        return info

def build_request(typ, **kwargs):
        if typ == 0x01:
                # discover - requires mac
                mac = kwargs['mac']
                body = struct.pack("6B", *mac)
        if typ == 0x03:
                # static network configuration
                mac = kwargs['mac']
                auth = kwargs['auth']
                ipaddr = kwargs['ipaddr']
                subnet = kwargs['subnet']
                gateway = kwargs['gateway']
                body = struct.pack("4B", *ipaddr)
                body += struct.pack("4B", *subnet)
                body += struct.pack("4B", *gateway)
                body += struct.pack("6B", *mac)
                body += struct.pack("B", len(auth)) + auth
        if typ == 0x05:
                # reboot - requires mac, auth
                mac = kwargs['mac']
                auth = kwargs['auth']
                body = struct.pack("6B", *mac)
                body += struct.pack("B", len(auth)) + auth
        if typ == 0x07:
                # dhcp - requires mac, auth, 
                mac = kwargs['mac']
                auth = kwargs['auth']
                body = struct.pack("B", 1)
                body += struct.pack("6B", *mac)
                body += struct.pack("B", len(auth)) + auth
        return build_frame(typ, body)

def build_response(info):
        resp = None
        if info['code'] == 0x01:
                flds = {0x01: (0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
                                0x02: (1, 1, 1, 1),
                                0x03: (255, 255, 255, 0),
                                0x04: "test",
                                0x0b: (1, 1, 1, 1),
                                0x0d: "ADDP Emulator",
                                #0x10: 0,
                                0x07: 0,
                                0x08: "V.1 04-25-2013",
                                0x0e: 771,
                                0x13: 1027,
                                0x12: 1}
                resp = build_frame(0x02, build_fields(flds))
        elif info['code'] == 0x05:
                flds = {0x01: (0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
                                0x09: "Operation FOO",
                                0x0a: 0,
                                0x11: 0}
                resp = build_frame(0x06, build_fields(flds))

        return resp

def parse_response(body):
        info = {}
        while body != b"":
                code = body[0]
                ln = body[1]
                fld = body[2:ln+2]
                body = body[ln+2:]

                info[fld_codes[code][0]] = fld_codes[code][2](fld)

        return info

def code_16_parser(x):
        if len(x) == 1:
                return ord(x)
        elif len(x) == 4:
                return struct.unpack("BBBB", x)
        else:
                return x
