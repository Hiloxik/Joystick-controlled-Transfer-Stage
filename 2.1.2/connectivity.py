from ctypes import *
import os
import sys

# library and serial numbers
if sys.version_info < (3, 8):
    os.chdir(r"C:\Program Files\Thorlabs\Kinesis")
else:
    os.add_dll_directory(r"C:\Program Files\Thorlabs\Kinesis")

lib_servo: CDLL = cdll.LoadLibrary("Thorlabs.MotionControl.KCube.DCServo.dll")
lib_inertial: CDLL = cdll.LoadLibrary("Thorlabs.MotionControl.KCube.InertialMotor.dll")

# Form function to execute a command
def call_lib(device_type, command, *args):
    lib = lib_servo if device_type == "servo" else lib_inertial
    prefix = "CC_" if device_type == "servo" else "KIM_"
    command_method = getattr(lib, prefix + command, None)
    if command_method is not None:
        return command_method(*args)
    else:
        raise Exception(f"Invalid command {command} for device type {device_type}")

# Connect a device
def connect_device(device_serial_num, device_type, device_channel):
    if device_channel is None:
        if lib_servo.TLI_BuildDeviceList() == 0:
            lib_servo.TLI_InitializeSimulations()
            if call_lib(device_type, "Open", device_serial_num) == 0:
                    call_lib(device_type, "StartPolling", device_serial_num, c_int(200))
                    print(f"Device {device_serial_num.value.decode()} connected successfully.")
                    return f"Device {device_serial_num.value.decode()} connected successfully."
            else:
                print(f"Device {device_serial_num.value.decode()} connected failed.")
                return f"Device {device_serial_num.value.decode()} connection failed."
        else:
            return "No devices found."
    else:
        if lib_inertial.TLI_BuildDeviceList() == 0:
            lib_inertial.TLI_InitializeSimulations()
            if call_lib(device_type, "Open", device_serial_num) == 0 and call_lib(device_type, "EnableChannel", device_serial_num, c_int(int(device_channel))) == 0:
                call_lib(device_type, "StartPolling", device_serial_num, c_int(200))
                print(f"Device {device_serial_num.value.decode()} Channel {device_channel} connected successfully.")
                return f"Device {device_serial_num.value.decode()} Channel {device_channel} connected successfully."
            else:
                print(f"Device {device_serial_num.value.decode()} Channel {device_channel} connected failed.")
                return f"Device {device_serial_num.value.decode()} Channel {device_channel} connection failed."
        else:
            return "No devices found."

# Disconnect a device
def disconnect_device(device_serial_num, device_type, device_channel):
    if device_type == 'inertial':
        call_lib(device_type, "DisableChannel", device_serial_num, c_int(int(device_channel)))
        call_lib(device_type, "StopPolling", device_serial_num)
        call_lib(device_type, "Close", device_serial_num)
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} disconnected successfully."
    else:
        call_lib(device_type, "Close", device_serial_num)
        return f"Device {device_serial_num.value.decode()} disconnected successfully."

# Check device connection
def is_connected(device_serial_num, device_type, device_channel):
    if device_type == 'servo':
        return call_lib(device_type, "Open", device_serial_num) == 0, "No devices connected."
    if device_type == 'inertial':
        return call_lib(device_type, "Open", device_serial_num) == 0 and call_lib(device_type, "EnableChannel", device_serial_num, c_int(int(device_channel))) == 0, "No devices connected."