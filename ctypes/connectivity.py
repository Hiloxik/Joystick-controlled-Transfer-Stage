from tkinter import messagebox
from ctypes import *
import os
import sys

# library and serial number
if sys.version_info < (3, 8):
    os.chdir(r"C:\Program Files\Thorlabs\Kinesis")
else:
    os.add_dll_directory(r"C:\Program Files\Thorlabs\Kinesis")

lib: CDLL = cdll.LoadLibrary("Thorlabs.MotionControl.KCube.DCServo.dll")
serial_num1 = c_char_p(b"27004354")
serial_num2 = c_char_p(b"27256127")
serial_num3 = c_char_p(b"27256510")
serial_num4 = c_char_p(b"55152924")
serial_num5 = c_char_p(b"97100512")
serial_num6 = c_char_p(b"97100512")
serial_num7 = c_char_p(b"97100512")
serial_num8 = c_char_p(b"97100512")

def connect_device(device_serial_num):
    if lib.TLI_BuildDeviceList() == 0:
        if lib.CC_Open(device_serial_num) == 0:
            lib.CC_StartPolling(device_serial_num, c_int(200))
            print(f"Device {device_serial_num.value.decode()} connected successfully.")
            return f"Device {device_serial_num.value.decode()} connected successfully."
        else:
            print(f"Device {device_serial_num.value.decode()} connected failed.")
            return f"Device {device_serial_num.value.decode()} connection failed."
    else:
        return "Connect", "No devices found."

def disconnect_device(device_serial_num):
    lib.CC_Close(device_serial_num)
    return f"Device {device_serial_num.value.decode()} disconnected successfully."

def is_connected(device_serial_num):
    return lib.CC_Open(device_serial_num) == 0, "No devices connected."