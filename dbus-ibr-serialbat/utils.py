# -*- coding: utf-8 -*-
import logging
import serial
from time import sleep
from struct import *

# Logging
format = "%(asctime)s %(levelname)s:%(name)s:%(message)s"
logging.basicConfig(level=logging.DEBUG, format=format, datefmt="%d.%m.%y_%X_%Z")
logger = logging.getLogger("SerialBattery")
logger.setLevel(logging.INFO)

# Open the serial port
# Return variable for the openned port 
def open_serial_port(port, baud):
    return serial.Serial(port, baudrate=baud, timeout=0.1)

def read_serial_garbage(ser, when):
    l = ser.inWaiting()
    while l:
        logger.info(f"read_serial_garbage ({when}): {l} bytes available...")
        res = ser.read(l)
        logger.info(f"read_serial_garbage: read {len(res)} bytes ...")
        sleep(0.05)
        l = ser.inWaiting()

# Read data from previously openned serial port
def read_serialport_data(ser, command, length_pos, length_check, length_fixed=None, length_size=None):

    try:
        read_serial_garbage(ser, "before");

        ser.write(command)
        ser.flushOutput()

        length_byte_size = 1
        if length_size is not None: 
            if length_size.upper() == 'H':
                length_byte_size = 2
            elif length_size.upper() == 'I' or length_size.upper() == 'L':
                length_byte_size = 4

        count = 0
        toread = ser.inWaiting()

        while toread < (length_pos+length_byte_size):
            sleep(0.005)
            toread = ser.inWaiting()
            count += 1
            if count > 150:
                # logger.error(">>> ERROR: No reply - returning")
                return False
                
        #logger.info('serial data toread ' + str(toread))
        res = ser.read(toread)
        if length_fixed is not None:
            length = length_fixed
        else:
            if len(res) < (length_pos+length_byte_size):
                logger.error(">>> ERROR: No reply - returning [len:" + str(len(res)) + "]")
                return False
            length_size = length_size if length_size is not None else 'B'
            length = unpack_from('>'+length_size, res,length_pos)[0]
            
        #logger.info('serial data length ' + str(length))

        count = 0
        data = bytearray(res)
        while len(data) <= length + length_check:
            res = ser.read((length + length_check) - len(data) + 1)
            data.extend(res)
            #logger.info('serial data length ' + str(len(data)))
            sleep(0.005)
            count += 1
            if count > 150:
                logger.error(">>> ERROR: No reply - returning [len:" + str(len(data)) + "/" + str(length + length_check) + "]")
                return False

        sleep(0.05)
        read_serial_garbage(ser, "after");
        return data

    except serial.SerialException as e:
        logger.exception(e)
        logger.error(f"read_serialport_data(): exception caught...")
        raise

def read_serialport_data_fixed(ser, command, length):

    try:
        read_serial_garbage(ser, "before");

        ser.write(command)
        ser.flushOutput()

        count = 0
        data = bytearray()
        while len(data) < length:
            res = ser.read(length - len(data))
            if res:
                data.extend(res)
                # logger.info(f"read {len(data)} of {length} bytes...")
            
            if len(data) == length:
                break

            sleep(0.1)
            count += 1
            if count > 10: # Timeout: 1s
                # logger.error(f"timeout, read {len(data)} of {length} bytes")
                return False

        sleep(0.05)
        read_serial_garbage(ser, "after");
        return data

    except serial.SerialException as e:
        logger.exception(e)
        logger.error(f"read_serialport_data_fixed(): exception caught...")
        raise



