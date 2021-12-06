#! /usr/bin/env python3
# SPDX-License-Identifier: Unlicense

import sys
import time
import socket
import requests  # external dependency


class Nanoleaf:

    DEFAULT_PORT = '16021'
    API_PREFIX = '/api/v1/'

    def __init__(self, target, token=None):
        self.session = requests.Session()
        self.session.hooks = {
            'response': lambda r, *args, **kwargs: r.raise_for_status()
        }
        if ':' in target:
            self.target = target
        else:
            self.target = target + ':' + self.DEFAULT_PORT
        self._url = 'http://' + self.target + self.API_PREFIX
        self.token = token

    def __eq__(self, other):
        return self.url() == other.url()

    def __repr__(self):
        return self.url()

    def url(self, endpoint=''):
        if self.token:
            return self._url + self.token + '/' + endpoint
        else:
            return self._url + endpoint

    def add_user(self):
        response = self.session.post(self.url('new'))
        self.token = response.json()['auth_token']

    def del_user(self):
        self.session.delete(self.url())


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

    if sys.argv[1] == '-h':  # command line help
        print("usage: %s [target] [[-]token]" % sys.argv[0])
        print("\t\t* search devices if no target")
        print("\t\t* get a token if none provided")
        print("\t\t* delete the token if minus-prefixed")
        sys.exit()

    target = sys.argv[1]

    if len(sys.argv) == 2:  # get an authentication token
        print("no token provided, getting one...")
        nanoleaf = Nanoleaf(target)
        try:
            nanoleaf.add_user()
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 403:
                print("ERROR 403")
                print("\thold the power button down until controller blink")
                print("\tand try again within 30 seconds")
                sys.exit(1)
            else:
                raise
        print("token: %s" % nanoleaf.token)
        sys.exit()

    token = sys.argv[2]

    if token.startswith('-'):  # delete the token
        token = token[1:]
        nanoleaf = Nanoleaf(target, token)
        nanoleaf.del_user()
        print("token %s deleted" % nanoleaf.token)
        sys.exit()