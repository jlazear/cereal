cereal
======

Threaded buffered drop-in replacement for pyserial.Serial.

Docs
====
jlazear

6/20/13

Cereal is a drop-in replacement for the PySerial Serial class that
continuously buffers any received data from the port in memory.

A substitute for the PySerial serial.Serial class that continuously
buffers any received data from the port in memory. This allows us to
bypass buffer problems, e.g. the linux serial driver's hard-coded
4096 character read buffer.

Cereal replicates the behavior of serial.Serial, so any scripts
utilizing Serial should be able to use Cereal instead without
changing anything, as long as your are using the fairly simple
features of Serial, e.g., Cereal may not be used as a generator.

Cereal owns an instance of Serial (Cereal.ser), so one may still
use the underlying properties of Serial if so desired. Be warned,
though, that using the underlying Serial instance may interfere
with Cereal's buffering and cause problems. Be very careful if you
do this!

Cereal's buffer and all read commands should be thread-safe.

Cereal.timeout is meaningless less than 0.01, since the read
command only checks if the timeout has been exceeded every 0.01
seconds. This is done to prevent excess CPU usage by an instance
of Cereal whose read() method is being called very rapidly.

The following example usage transparently replaces serial.Serial
instances with cereal.Cereal instances, without having to modify
pre-existing code. It falls back on serial.Serial instances if cereal
is unavailable.

Example usage:

	import warnings
	try:
	    from cereal import Cereal as Serial
	except ImportError:
	    warningtext = ("cereal module not found. Using serial instead. This "
	                   "will probably\n work, but the cereal module is "
	                   "strongly preferred.")
	    warnings.warn(warningtext)
	    from serial import Serial

	ser = Serial('/dev/tty-USB1')
	ser.read(1)
	ser.write('hello\n')