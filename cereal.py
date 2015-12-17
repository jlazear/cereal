"""
cereal.py
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
    warningtext = \
"cereal module not found. Using serial instead. This will probably\n\
work, but the cereal module is strongly preferred."
    warnings.warn(warningtext)
    from serial import Serial
"""
version = 130620
releasestatus = 'dev'


import serial
import threading
import time


class Cereal(threading.Thread):
    """
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
    """
    # Variables with these names should not be passed to the
    # underlying serial connection object.
    localvars = ('ser', 'timeout', 'buffer', 'running')

    def __init__(self, *args, **kwargs):
        self.ser = serial.Serial(*args, **kwargs)

        # Create a threading.Event to control the thread's existence
        self.stopped = threading.Event()  # Events default to False
        self.stopped.set()

        # Create buffer to hold serial port's contents, and associated
        # lock
        self.buffer = ''
        self.bufferlock = threading.RLock()

        threading.Thread.__init__(self)
        self.openflag = ('open=True' in repr(self.ser))
        self.ser.timeout = 0.1
        try:
            self.timeout = args[5]
        except IndexError:
            if 'timeout' in kwargs:
                self.timeout = kwargs['timeout']
            else:
                self.timeout = 0

        # Copy Serial's methods' docstrings to Cereal's methods
        cdir = set(dir(self))
        sdir = set(dir(serial.Serial))

        # Find methods common to Serial and Cereal, excluding hidden ones
        intersection = cdir & sdir
        ic = intersection.copy()
        for item in intersection:
            if '__' in item:
                ic.remove(item)

        # Replace the method's docstring (note: methods get their
        # docstrings from their underlying functions method.__func__)
        for name in ic:
            doc = getattr(getattr(serial.Serial, name), '__doc__')
            method = getattr(self, name)
            try:
                methodfunc = getattr(method, '__func__')
                setattr(methodfunc, '__doc__', doc)
            except AttributeError:      # Gets here if 'method' is an
                pass                    # attribute instead of a
                                        # method

        if self.openflag:
            self.stopped.clear()
            try:
                self.start()
            except RuntimeError:
                pass

    def __del__(self):
        self.close()
        self.stop()

    def __str__(self):
        return self.__repr__() + self.ser.__repr__()[6:]

    def stop(self):
        self.ser.close()
        if self.isAlive():
            self.stopped.set()
            self.join()

    def run(self):
        while not self.stopped.isSet():
            try:
                if self.openflag:
#                    self.ser.open()
                    try:
                        iw = self.ser.inWaiting()
                        iw = max(1, int(iw))
                        toadd = self.ser.read(self.ser.inWaiting())
                    except (ValueError, TypeError):
                        toadd = ''
                    except (OSError, serial.SerialException):
                        toadd = ''
                    with self.bufferlock:
                        self.buffer += toadd
                time.sleep(0.1)
            except KeyboardInterrupt:
                self.stopped.set()

    def _read(self, size=1):
        with self.bufferlock:
            toret = self.buffer[:size]
            self.buffer = self.buffer[size:]
            return toret

    def __setattr__(self, name, value):
        if name not in self.localvars:
            setattr(self.ser, name, value)
        # setattr(self, name, value)
        object.__setattr__(self, name, value)

    ######################################
    ########### Serial methods ###########
    ######################################

    def open(self):
        self.ser.open()
        self.openflag = True
        if self.stopped.is_set():
            self.stopped.clear()
        if self.is_alive() is False:
            try:
                self.start()
            except RuntimeError:
                pass

    def close(self):
        self.ser.close()
        self.openflag = False

    def read(self, size=1):
#        self.ser.open()
        with self.bufferlock:
            l = len(self.buffer)
            if l >= size:
                return self._read(size)
            t0 = time.time()
            t = time.time()
            while (t - t0) <= self.timeout:  # Waiting for data to arrive
                if l >= size:
                    return self._read(size)
                l = len(self.buffer)
                time.sleep(0.01)
                t = time.time()
            return self._read(len(self.buffer))    # Return timeout value

    def _unsafe_read(self, size=1):
#        self.ser.open()
        l = len(self.buffer)
        if l >= size:
            return self._read(size)
        t0 = time.time()
        t = time.time()
        while (t - t0) <= self.timeout:  # Waiting for data to arrive
            if l >= size:
                return self._read(size)
            l = len(self.buffer)
            time.sleep(0.01)
            t = time.time()
        return self._read(len(self.buffer))    # Return timeout value

    def readline(self, size=None, eol='\n'):
        eollen = len(eol)
        with self.bufferlock:
            t0 = time.time()
            t = -1.
            while (t - t0) <= self.timeout:
                index = self.buffer.find(eol)
                if index != -1:
                    return self.read(index + eollen)
                else:
                    time.sleep(.01)
                t = time.time()
            return ''

    def write(self, data):
#        self.ser.open()
        return self.ser.write(data)

    def inWaiting(self):
        with self.bufferlock:
            l = len(self.buffer)
        return l

    def flush(self):
#        self.ser.open()
        return self.ser.flush()

    def flushInput(self):
#        self.ser.open()
        with self.bufferlock:
            self.buffer = ''
        return self.ser.flushInput()

    def flushOutput(self):
#        self.ser.open()
        return self.ser.flushOutput()

    def sendBreak(self, duration=0.25):
#        self.ser.open()
        return self.ser.sendBreak(duration)

    def setBreak(self, level=True):
#        self.ser.open()
        return self.ser.setBreak(level)

    def setRTS(self, level=True):
#        self.ser.open()
        return self.ser.setRTS(level)

    def setDTR(self, level=True):
#        self.ser.open()
        return self.ser.setDTR(level)

    def getCTS(self):
#        self.ser.open()
        return self.ser.getCTS()

    def getDSR(self):
#        self.ser.open()
        return self.ser.getDSR()

    def getRI(self):
#        self.ser.open()
        return self.ser.getRI()

    def getCD(self):
#        self.ser.open()
        return self.ser.getCD()
