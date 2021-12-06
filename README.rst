Nanoleaf API client for Python
==============================

This is a library and tooling for `Nanoleaf products <https://nanoleaf.me>`_.

The API is `documented by Nanoleaf <https://forum.nanoleaf.me/docs>`_.

The goal is to provide a minimal thin layer to use these devices in Python,
with the help of the module ``requests``.


Devices Discovery
-----------------

The class ``NanoleafZeroconf`` helps to print device information
when discovered with the Python module ``zeroconf``.

It can be integrated in an application as following:

.. code-block:: python

   import zeroconf
   with zeroconf.Zeroconf() as zc:
       zc.add_service_listener(NanoleafZeroconf.SERVICE, NanoleafZeroconf())

Or it can be simply used as a tool without any argument::

   ./nanoleaf.py

The output includes the device name, the IP address with TCP port,
the hardware model and the firmware version.


Authentication Token
--------------------

The Nanoleaf REST API is using a token in each HTTP request
in order to authenticate a user of the device.

In order to get a new token, the device must be set in pairing state
by holding the on/off button during 5-7 seconds.
When the controller lights start flashing,
a token can be requested within 30 seconds::

   ./nanoleaf.py 192.168.1.128

A token can be revoked by using the sign "minus" as a prefix::

   ./nanoleaf.py 192.168.1.128 -myc0mpl1c4tetok3n

When specifying the token without "minus" on the command line,
some information is queried and the light is flashing::

   ./nanoleaf.py 192.168.1.128 myc0mpl1c4tetok3n


Basic Requests
--------------

The main class of the library is ``Nanoleaf`` and requires two arguments:

#. Target location (i.e. IP address and TCP port separated by a colon).
   If no port is specified, the default port is assumed.
#. Authentication token (none when requesting one).

Note: the special methods ``__eq__`` and ``__repr__`` are implemented.

Once initialized, the ``Nanoleaf`` instance will use
a single session for all requests.

An exception is raised if an error occurs.

The API requests are implemented in more or less specialized class methods.
Some methods are for exactly one specific request,
while other methods are flexible thanks to some parameters:

* The methods ``get`` and ``put`` are fully generic and called by other ones.
* The methods ``query``, ``set`` and ``update`` are a bit more specialized
  for color states. They are used to implement some properties.
* The method ``identify`` is only for flashing lights.

Most API endpoints are managed as properties:

* ``power`` is a boolean read/write property to manage on/off state.

  .. code-block:: python

     nanoleaf.power = True

* ``color_mode`` is the read-only current mode.
  Its value is changed when setting other properties.

* ``ct``, ``hue``, ``sat`` and ``brightness``
  can be updated with the operators ``=``, ``+=`` and ``-=``.
  These properties have 3 members: ``min``, ``max`` and ``value``
  which is implicitly returned when the property is converted as ``int``.

  .. code-block:: python

     nanoleaf.hue += 300
     print("hue: %d (max: %d)" % (nanoleaf.hue, nanoleaf.hue.max))

* ``brightness`` fading can be specified in seconds
  if assigned with a tuple ``(value, duration)``.

  .. code-block:: python

     nanoleaf.brightness = (50, 3)

* ``effects`` is the read-only list of available effects.
* ``effect`` is the current effect.

  .. code-block:: python

     nanoleaf.effect = nanoleaf.effects[3]

* The ``orientation`` of the controller is in counter clockwise degrees.


Events
------

Some high-level events may be received slowly
by providing a callback function to the method ``listen_events``.

The event messaging uses a Server-Sent Events (SSE) stream,
so it requires a dedicated Python module for receiving:
either ``sseclient`` or ``sseclient-py``.

It is recommended to receive events in a daemon thread:

.. code-block:: python

   from threading import Thread
   def print_event(event, nanoleaf, user_data):
       print(event)
   Thread(daemon=True, target=nanoleaf.listen_events,
          args=(list(nanoleaf.EventType), print_event)).start()

There are 4 types of events managed by this method:

#. ``EventType.STATE`` for ``EventState``.
#. ``EventType.LAYOUT`` for ``EventLayout``.
#. ``EventType.EFFECT``.
#. ``EventType.TOUCH`` for ``EventGesture``.
