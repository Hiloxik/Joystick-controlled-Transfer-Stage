from ctypes import *
from connectivity import is_connected, lib
import time

# This function now uses the specific serial number passed to it.
def get_current_position(device_serial_num):
    connecton_status, _ = is_connected(device_serial_num)
    if not connecton_status:
        return f"Device {device_serial_num.value.decode()} is not connected."

    lib.CC_RequestPosition(device_serial_num)
    time.sleep(0.2)
    dev_pos = c_double(lib.CC_GetPosition(device_serial_num))

    return dev_pos.value