from tkinter import messagebox
from ctypes import *
from connectivity import is_connected, lib
import time
import threading

stop_flag = False  # Define stop_flag in the global scope


def home_device(device_serial_num):
    connecton_status, _ = is_connected(device_serial_num)
    if not connecton_status:
        return f"Device {device_serial_num.value.decode()} is not connected."
    lib.CC_Home(device_serial_num)
    time.sleep(0.1)
    return f"Device {device_serial_num.value.decode()} homed successfully."


# This function now accepts a movement direction parameter.
def move_device(device_serial_num, direction, step, velocity):
    connecton_status, _ = is_connected(device_serial_num)
    if not connecton_status:
        return f"Device {device_serial_num.value.decode()} is not connected."
    
    new_vel_param = c_int(int(velocity))
    lib.CC_SetVelParams(device_serial_num, new_vel_param)

    lib.CC_RequestPosition(device_serial_num)
    # time.sleep(0.01)
    dev_pos = c_int(lib.CC_GetPosition(device_serial_num))

    new_pos_real = c_int(int(step))  # in real units

    new_pos_dev = c_int(dev_pos.value + new_pos_real.value) if direction else c_int(dev_pos.value - new_pos_real.value)
    print(new_pos_dev)

    lib.CC_SetMoveAbsolutePosition(device_serial_num, new_pos_dev)
    # time.sleep(0.25)
    lib.CC_MoveAbsolute(device_serial_num)
    return f"Device {device_serial_num.value.decode()} moved successfully."


class DeviceDriver:
    def __init__(self):
        self.stop_event = threading.Event()

    def drive_device(self, device_serial_num, direction, step, velocity):
        connection_status, _ = is_connected(device_serial_num)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."

        # convert the velocity to a proper step for the move_device
        # step = 50000 # You may want to adjust this according to your needs
        new_vel_param = c_int(int(velocity))
        lib.CC_SetVelParams(device_serial_num, new_vel_param)

        if direction == 'stop':
            self.stop_event.set()
        else:
            self.stop_event.clear()
            while connection_status and not self.stop_event.is_set():
                # Move the device continuously without a defined step size.
                if direction == 'right':
                    # move_device(device_serial_num, True, step, velocity)
                    lib.CC_GetMMIParamsExt(device_serial_num, 1, c_int(int(10000)), c_int(int(100000)))

                    
                    
                elif direction == 'left':
                    move_device(device_serial_num, False, step, velocity)
                time.sleep(0.01)  # Add delay here

        if self.stop_event.is_set():
            stop_device(device_serial_num)  # stop the device here
            self.stop_event.clear()  # reset the flag for future operations
            return f"Device {device_serial_num.value.decode()} stopped moving."
        return f"Device {device_serial_num.value.decode()} is moving."


    def start_drive(self, device_serial_num, direction, step, velocity):
        self.stop_event.clear()
        self.drive_thread = threading.Thread(target=self.drive_device, args=(device_serial_num, direction, step, velocity))
        self.drive_thread.start()
        connection_status, _ = is_connected(device_serial_num)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        return f"Device {device_serial_num.value.decode()} is moving."
    
    def stop_drive(self):
        self.stop_event.set()  # Signal the thread to stop

def stop_device(device_serial_num):
    connecton_status, _ = is_connected(device_serial_num)
    if not connecton_status:
        return f"Device {device_serial_num.value.decode()} is not connected."
    lib.CC_StopImmediate(device_serial_num)
    return f"Device {device_serial_num.value.decode()} stopped successfully."

def set_step(device_serial_num, step):
    connecton_status, _ = is_connected(device_serial_num)
    if not connecton_status:
        return f"Device {device_serial_num.value.decode()} is not connected."

    step = c_int(int(step))
    return f"Step parameter set successfully for device {device_serial_num.value.decode()}."


def set_velocity(device_serial_num, new_vel_param):
    connecton_status, _ = is_connected(device_serial_num)
    if not connecton_status:
        return f"Device {device_serial_num.value.decode()} is not connected."
    new_vel_param = c_int(int(new_vel_param))
    lib.CC_SetVelParams(device_serial_num, new_vel_param)
    return f"Velocity parameters set successfully for device {device_serial_num.value.decode()}."

# def get_current_velocity(device_serial_num):
#     connecton_status, _ = is_connected(device_serial_num)
#     if not connecton_status:
#         return None, f"Device {device_serial_num.value.decode()} is not connected."
#     current_velocity = lib.CC_GetVelParams(device_serial_num)
#     return current_velocity, f"Velocity fetched successfully for device {device_serial_num.value.decode()}."

# CC_SetRotationModes(char const * serialNo, MOT_MovementModes mode, MOT_MovementDirections direction)
# CC_SetJogMode(char const * serialNo, MOT_JogModes mode, MOT_StopModes stopMode)
# CC_MoveAtVelocity(char const * serialNo, MOT_TravelDirection direction)