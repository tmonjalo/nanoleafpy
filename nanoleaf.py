#! /usr/bin/env python3
# SPDX-License-Identifier: Unlicense

from enum import Enum
import sys
import time
import json
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
        self.touch_events = self.UDP()

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

    def get(self, endpoint=''):
        return self.session.get(self.url(endpoint)).json()

    def put(self, endpoint, body=None):
        self.session.put(self.url(endpoint), json=body)

    def identify(self):
        """Make lights flashing."""
        self.put('identify')

    def query(self, endpoint='', suffix='value'):
        return self.get('state/' + endpoint + '/' + suffix)

    def set(self, endpoint, value, duration=0):
        body = {'value': value}
        if duration:  # fading
            body['duration'] = duration
        self.put('state', {endpoint: body})

    def update(self, endpoint, diff):
        """State values can be updated with increment."""
        self.put('state', {endpoint: {'increment': diff}})

    class BoolState():

        def __init__(self, endpoint):
            self.endpoint = endpoint

        def __get__(self, device, devclass):
            return device.query(self.endpoint)

        def __set__(self, device, value):
            device.set(self.endpoint, value)

    power = BoolState('on')

    class ColorMode(Enum):
        EFFECT = 'effect'
        TEMP = 'ct'
        HS = 'hs'

    @property
    def color_mode(self):
        """Can be one of ColorMode values."""
        return self.ColorMode(self.get('state/colorMode'))

    class MinMaxState():

        def __init__(self, device, endpoint):
            self.device = device
            self.endpoint = endpoint

        @property
        def value(self):
            return self.device.query(self.endpoint)

        @property
        def min(self):
            return self.device.query(self.endpoint, 'min')

        @property
        def max(self):
            return self.device.query(self.endpoint, 'max')

        def __int__(self):
            return self.value

        def __iadd__(self, diff):
            self.device.update(self.endpoint, diff)
            return None  # skip implicit assignment

        def __isub__(self, diff):
            self.device.update(self.endpoint, -diff)
            return None  # skip implicit assignment

    class IntState():

        def __init__(self, endpoint):
            self.endpoint = endpoint

        def __get__(self, device, devclass):
            return devclass.MinMaxState(device, self.endpoint)

        def __set__(self, device, value):
            if isinstance(value, int):
                device.set(self.endpoint, value)
            elif isinstance(value, tuple):  # fading
                device.set(self.endpoint, value[0], value[1])

    ct = IntState('ct')
    hue = IntState('hue')
    sat = IntState('sat')
    bri = IntState('brightness')
    brightness = IntState('brightness')

    @property
    def effect(self):
        return self.get('effects/select')

    @effect.setter
    def effect(self, name):
        self.put('effects', {'select': name})

    @property
    def effects(self):
        return self.get('effects/effectsList')

    @property
    def layout(self):
        return self.get('panelLayout/layout')

    @property
    def orientation(self):
        return self.get('panelLayout/globalOrientation/value')

    @orientation.setter
    def orientation(self, angle):
        """The angle is counter clockwise."""
        self.put('panelLayout', {'globalOrientation': {'value': angle}})

    class EventType(Enum):
        STATE = 1
        LAYOUT = 2
        EFFECT = 3
        TOUCH = 4

    class EventState(Enum):
        POWER = 1
        BRIGHTNESS = 2
        HUE = 3
        SATURATION = 4
        COLOR_TEMP = 5
        COLOR_MODE = 6

    class EventLayout(Enum):
        PANELS = 1
        ORIENTATION = 2

    class EventGesture(Enum):
        TAP_SINGLE = 0
        TAP_DOUBLE = 1
        SWIPE_UP = 2
        SWIPE_DOWN = 3
        SWIPE_LEFT = 4
        SWIPE_RIGHT = 5
        HOLD = 6

    def listen_events(self, types, sse_notifier=None, user_data=None):
        """Receive Server-Sent Events (SSE).

        types is a set of EventType to be notified.
        sse_notifier is called with (event dict, Nanoleaf, user_data).
        If EventType.TOUCH is in types:
           - EventGesture is received in sse_notifier
           - EventTouch is received in touch_notifier
             if listen_touch_events is already running.
        """
        url = self.url('events?id=' + ','.join([str(t.value) for t in types]))
        headers = {}
        if self.touch_events.is_open():
            headers['TouchEventsPort'] = str(self.touch_events.port)
        from sseclient import SSEClient  # external dependency
        if hasattr(SSEClient, 'events'):  # module sseclient-py
            stream = self.session.get(url, headers=headers, stream=True)
            sse = SSEClient(stream).events()
        else:  # module sseclient
            sse = SSEClient(url, session=self.session, headers=headers)
        self.sse_stop = False
        if not sse_notifier:  # keep stream open for touch events
            while not self.sse_stop:
                time.sleep(1)
            return
        for events in sse:
            for event in json.loads(events.data)['events']:
                event_type = self.EventType(int(events.id))
                event['type'] = event_type
                if event_type is self.EventType.STATE:
                    event['attr'] = self.EventState(event['attr'])
                elif event_type is self.EventType.LAYOUT:
                    event['attr'] = self.EventLayout(event['attr'])
                elif event_type is self.EventType.TOUCH:
                    event['gesture'] = self.EventGesture(event['gesture'])
                    panel = event['panelId']
                    event['panel'] = panel if panel >= 0 else None
                sse_notifier(event, self, user_data)
                if self.sse_stop:
                    return

    def close_events(self):
        """Close after receiving the next event."""
        self.sse_stop = True

    class EventTouch(Enum):
        HOVER = 0
        DOWN = 1
        HOLD = 2
        UP = 3
        SWIPE = 4
        TAP = 5  # undocumented

    def listen_touch_events(self, touch_notifier=None, user_data=None):
        """Receive detailed touch events via UDP.

        Must be called before listen_events.
        touch_notifier is called with (event dict, Nanoleaf, user_data).
        """
        self.touch_events.open()
        while self.touch_events.is_open():
            data = self.touch_events.recv()
            num = data[0] << 8 | data[1]
            i = 2
            while num:
                event = {}
                event['panel'] = data[i + 0] << 8 | data[i + 1]
                event['type'] = self.EventTouch((data[i + 2] & 0x70) >> 4)
                event['strength'] = (data[i + 2] & 0xf)
                panel = data[i + 3] << 8 | data[i + 4]
                if panel == 0xffff:
                    panel = None
                event['from'] = panel
                touch_notifier(event, self, user_data)
                i += 5
                num -= 1

    def close_touch_events(self):
        self.touch_events.close()

    class UDP:

        def __init__(self):
            self.socket = None
            self.port = 0

        def open(self):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            port = 10000
            for attempt in range(9999):
                try:
                    sock.bind(('', port))
                except OSError as error:
                    last_error = error
                    port += 1
                else:
                    break
            else:
                raise last_error
            self.socket = sock
            self.port = port

        def is_open(self):
            return self.port != 0

        def recv(self):
            return self.socket.recv(2048)

        def close(self):
            self.port = 0
            if self.socket:
                self.socket.close()
                self.socket = None


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

    # flash lights and get information
    nanoleaf = Nanoleaf(target, token)
    nanoleaf.identify()
    info = nanoleaf.get()
    print("%s %s / serial %s / model %s / version %s / firmware %s" %
          (info['manufacturer'], info['name'], info['serialNo'], info['model'],
           info['hardwareVersion'], info['firmwareVersion']))
    state = info['state']
    if 'on' in state:
        print("state: %s" % ('on' if state['on']['value'] else 'off'))
    if 'colorMode' in state:
        print("color mode: %s" % state['colorMode'])
    if 'ct' in state:
        print("color temperature: %s" % state['ct'])
    if 'hue' in state:
        print("hue: %s" % state['hue'])
    if 'sat' in state:
        print("saturation: %s" % state['sat'])
    if 'brightness' in state:
        print("brightness: %s" % state['brightness'])

    # listen for all events
    from threading import Thread
    def print_event(event, nanoleaf, user_data):
        print(event)
    Thread(daemon=True, target=nanoleaf.listen_touch_events,
           args=(print_event,)).start()
    while not nanoleaf.touch_events.is_open():
        time.sleep(0.1)
    Thread(daemon=True, target=nanoleaf.listen_events,
           args=(list(nanoleaf.EventType), print_event)).start()
    input("listening for events...\n")
