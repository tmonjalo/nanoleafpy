#! /usr/bin/env python3
# SPDX-License-Identifier: Unlicense

import sys
import time
import socket


class NanoleafZeroconf:

    SERVICE = '_nanoleafapi._tcp.local.'

    @staticmethod
    def get_address(addresses):
        if addresses and len(addresses) > 0:
            return socket.inet_ntoa(addresses[0])
        else:
            return '?'

    @staticmethod
    def get_property(properties, key):
        if properties and key in properties:
            return str(properties[key], 'UTF-8')
        else:
            return '?'

    def add_service(self, zc, type, name):
        print(name)
        info = zc.get_service_info(type, name)
        if not info:
            return
        addr = self.get_address(info.addresses)
        port = info.port if info.port else '?'
        print("\tIPv4/TCP: %s:%d" % (addr, port))
        model = self.get_property(info.properties, b'md')
        version = self.get_property(info.properties, b'srcvers')
        print("\tfirmware/model: %s on %s" % (version, model))

    def update_service(self, zc, type, name):
        pass


if __name__ == '__main__':

    if len(sys.argv) == 1:  # discover devices via Zeroconf
        print("searching devices via Zeroconf... (use -h option for help)")
        import zeroconf  # external dependency
        with zeroconf.Zeroconf() as zc:
            zc.add_service_listener(NanoleafZeroconf.SERVICE,
                                    NanoleafZeroconf())
            time.sleep(3)
            sys.exit()
