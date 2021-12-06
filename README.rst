Nanoleaf API client for Python
==============================

This is a library and tooling for `Nanoleaf products <https://nanoleaf.me>`_.

The API is `documented by Nanoleaf <https://forum.nanoleaf.me/docs>`_.

The goal is to provide a minimal thin layer to use these devices in Python.


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
