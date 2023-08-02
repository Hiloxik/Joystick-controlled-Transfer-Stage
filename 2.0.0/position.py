from ctypes import *
from connectivity import *
import time


# Get real time position
def get_current_position(device_serial_num, device_type, device_channel):
    if device_channel is None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        call_lib(device_type, "RequestPosition", device_serial_num)

        time.sleep(0.2)
        dev_pos = c_double(call_lib(device_type, "GetPosition", device_serial_num))

        return dev_pos.value
    else:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel.value.decode()} is not connected."
        call_lib(device_type, "RequestCurrentPosition", device_serial_num, device_type)
        time.sleep(0.2)
        dev_pos = c_double(call_lib(device_type, "GetCurrentPosition", device_serial_num))

        return dev_pos.value