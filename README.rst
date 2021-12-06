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
