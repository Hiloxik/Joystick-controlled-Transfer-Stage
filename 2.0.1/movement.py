from tkinter import messagebox
from ctypes import *
from connectivity import *
import time
import threading

stop_flag = False  # Define stop_flag in the global scope

# Home a device
def home_device(device_serial_num, device_type, device_channel):
    if device_channel is not None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."
        call_lib(device_type, "Home", device_serial_num, c_int(int(device_channel)))
        time.sleep(0.1)
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} homed successfully."
    else:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        call_lib(device_type, "Home", device_serial_num)
        time.sleep(0.1)
        return f"Device {device_serial_num.value.decode()} homed successfully."

# Move a KDC device
def move_CCdevice(device_serial_num, device_type, device_channel, direction, step, velocity):
    if device_channel is None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."

        new_vel_param = c_int(int(velocity))
        call_lib(device_type, "SetVelParams", device_serial_num, new_vel_param)

        call_lib(device_type, "RequestPosition", device_serial_num)

        dev_pos = c_int(call_lib(device_type, "GetPosition", device_serial_num))

        new_pos_real = c_int(int(step))  # in real units
        call_lib(device_type, "SetJogStepSize", device_serial_num, new_pos_real)

        call_lib(device_type, "SetJogMode", device_serial_num, c_int(int(2)), c_int(int(1)))
        print(dev_pos)

        if direction:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(2)))
        else:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(1)))
        return f"Device {device_serial_num.value.decode()} moved successfully."

# Drive a KDC device
class DeviceCCDriver:
    def __init__(self):
        self.stop_event = threading.Event()

    def drive_device(self, device_serial_num, device_type, device_channel, direction, step, velocity):
        if device_channel is None:
            connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
            if not connection_status:
                return f"Device {device_serial_num.value.decode()} is not connected."

            new_vel_param = c_int(int(velocity))
            call_lib(device_type, "SetVelParams", device_serial_num, new_vel_param)

            if direction == 'stop':
                self.stop_event.set()
            else:
                self.stop_event.clear()
                while connection_status and not self.stop_event.is_set():
                    # Move the device continuously without a defined step size.
                    if direction == 'right':
                        move_CCdevice(device_serial_num, device_type, device_channel, True, step, velocity)

                    elif direction == 'left':
                        move_CCdevice(device_serial_num, device_type, device_channel, False, step, velocity)

                    time.sleep(0.01)  # Add delay here

            if self.stop_event.is_set():
                stop_device(device_serial_num, device_type, device_channel)  # stop the device here
                self.stop_event.clear()  # reset the flag for future operations
                return f"Device {device_serial_num.value.decode()} stopped moving."
            return f"Device {device_serial_num.value.decode()} is moving."

    def start_drive(self, device_serial_num, device_type, device_channel, direction, step, velocity):
        if device_channel is None:
            self.stop_event.clear()
            self.drive_thread = threading.Thread(target=self.drive_device,
                                                 args=(device_serial_num, device_type, device_channel, direction, step,
                                                       velocity))
            self.drive_thread.start()
            connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
            if not connection_status:
                return f"Device {device_serial_num.value.decode()} is not connected."
            return f"Device {device_serial_num.value.decode()} is moving."

    def stop_drive(self):
        self.stop_event.set()  # Signal the thread to stop

# Move a KIM device
def move_KIMdevice(device_serial_num, device_type, device_channel, direction, step, rate, acceleration, mode):
    if device_channel is not None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."

        call_lib(device_type, "RequestCurrentPosition", device_serial_num, device_type)
        dev_pos = c_int(call_lib(device_type, "GetCurrentPosition", device_serial_num, device_type))

        new_pos_param = c_int(int(step))
        new_rat_param = c_int(int(rate))
        new_acc_param = c_int(int(acceleration))
        new_mod_param = c_int(int(mode))

        print(new_pos_param, new_rat_param, new_acc_param)

        call_lib(device_type, "SetJogParameters", device_serial_num, c_int(int(device_channel)), new_mod_param,
                 new_pos_param, new_pos_param, new_rat_param, new_acc_param)

        print(dev_pos)

        if direction:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(device_channel)), c_int(int(2)))
        else:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(device_channel)), c_int(int(1)))
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} moved successfully."

# Drive a KIM device
def drive_KIMdevice(device_serial_num, device_type, device_channel, direction, maxvoltage, rate, acceleration):
    if device_channel is not None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."

        call_lib(device_type, "RequestCurrentPosition", device_serial_num, device_type)
        dev_pos = c_int(call_lib(device_type, "GetCurrentPosition", device_serial_num, device_type))

        new_vol_param = c_int(int(maxvoltage))
        new_rat_param = c_int(int(rate))
        new_acc_param = c_int(int(acceleration))

        call_lib(device_type, "RequestDriveOPParameters", device_serial_num, c_int(int(device_channel)))
        call_lib(device_type, "SetDriveOPParameters", device_serial_num, c_int(int(device_channel)), new_vol_param,
                 new_rat_param, new_acc_param)

        print(dev_pos)

        if direction:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(device_channel)), c_int(int(2)))
        else:
            call_lib(device_type, "MoveJog", device_serial_num, c_int(int(device_channel)), c_int(int(1)))
    return f"Device {device_serial_num.value.decode()} Channel {device_channel} moved successfully."

# Stop a device
def stop_device(device_serial_num, device_type, device_channel):
    if device_channel is not None:
        connecton_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connecton_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."
        call_lib(device_type, "MoveStop", device_serial_num, c_int(int(device_channel)))
        return f"Device {device_serial_num.value.decode()} Channel {device_channel} stopped successfully."
    else:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        call_lib(device_type, "StopImmediate", device_serial_num)
        return f"Device {device_serial_num.value.decode()} stopped successfully."

# Set move step for a KDC device
def set_CCstep(device_serial_num, device_type, device_channel, step):
    if device_channel is None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        step = c_int(int(step))
        call_lib(device_type, "SetJogStepSize", device_serial_num, step)
        return f"Step parameter set successfully for device {device_serial_num.value.decode()}."

# Set move velocity for a KDC device
def set_CCvelocity(device_serial_num, device_type, device_channel, new_vel_param):
    if device_channel is None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} is not connected."
        new_vel_param = c_int(int(new_vel_param))
        call_lib(device_type, "SetVelParams", device_serial_num, new_vel_param)
        return f"Velocity parameters set successfully for device {device_serial_num.value.decode()}."

# Set jog parameters for a KIM device
def set_KIMjog(device_serial_num, device_type, device_channel, mode, stepfor, steprev, rate, acceleration):
    if device_channel is not None:
        connection_status, _ = is_connected(device_serial_num, device_type, device_channel)
        if not connection_status:
            return f"Device {device_serial_num.value.decode()} Channel {device_channel} is not connected."
        stepfor = c_int(int(stepfor))
        steprev = c_int(int(steprev))
        rate = c_int(int(rate))
        acceleration = c_int(int(acceleration))
        call_lib(device_type, "SetJogParameters", device_serial_num, c_int(int(device_channel)), c_int(int(mode)),
                 stepfor, steprev, rate, acceleration)
        return f"Step parameter set successfully for device {device_serial_num.value.decode()} Channel {device_channel}."