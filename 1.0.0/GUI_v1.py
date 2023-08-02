import pygame
from threading import Thread
import tkinter as tk
from tkinter import messagebox
import tkinter as ttk
from ttkthemes import ThemedTk
from position import *
from connectivity import *
from movement import *
import time
from queue import Queue, Empty
import numpy as np
import logging


# These two functions process the real-time value of an axis on the joystick to a continuous motion command
def map_axis_to_step(axis, axis_value):
    # Microscope
    if axis == 4:
        DEAD_ZONE = 0.3
        max_step = 10
    # Stamp stage
    if axis == 2 or 3:
        DEAD_ZONE = 0.1
        max_step = 10
    # Sample stage
    else:
        DEAD_ZONE = 0.1
        max_step = 100

    if abs(axis_value) < DEAD_ZONE:
        return 0

    min_step = 0
    step = min_step + (abs(axis_value)) * (max_step - min_step)
    return step


def process_axis(device_name, i, axis, joystick_state, axis_device_command_mapping, command_position):
    direction = 'left' if axis < 0 else 'right'
    step = map_axis_to_step(i, axis)
    if step != 0 and i in axis_device_command_mapping:  # For non-zero velocity motion
        for device_index, command_index in axis_device_command_mapping[i]:
            if device_index < len(device_name):
                device = device_name[device_index]
                joystick_state[device][command_index] = True
                joystick_state[device][command_position] = [direction, step]


# Global joystick state dictionary
""" The typical form of joystick_state is a 13-element-command-dictionary: 
      {disconnect, connect, stop, moveCC forward, moveCC reverse, drive sample stage, drive sample stage (direction, velocity), 
       drive microscope, drive microscope (direction, velocity), drive stamp stage, drive stamp stage (direction, velocity), moveKIM forward, moveKIM reverse}.
    The initial form is [False] * 13. """
joystick_state = {}

stop_flag = False  # Define stop_flag in the global scope
# CURRENT_CCSTEP = 50000  # Initial CCstep
# CURRENT_CCVELOCITY = 1000  # Initial CCvelocity
# CURRENT_KIMSTEP = 500  # Initial KIMstep
# CURRENT_KIMRATE = 500  # Initial KIMrate
# CURRENT_KIMACCELERATION = 10000  # Initial KIMacceleration
# CURRENT_KIMJOGMODE = 1000 # Initial KIMjogmode
# CURRENT_KIMVOLTAGE = 20 # Initial KIMvoltage (for drive mode)

parameters = {
    "Microscope": {
        "CCstep": 500,
        "CCvelocity": 1000,
    },
    "Sample Stage X-Axis": {
        "CCstep": 500,
        "CCvelocity": 1000,
    },
    "Sample Stage Y-Axis": {
        "CCstep": 500,
        "CCvelocity": 1000,
    },
    "Sample Stage Rotator": {
        "CCstep": 500,
        "CCvelocity": 1000,
    },
    "Stamp Stage X-Axis": {
        "KIMstep": 500,
        "KIMrate": 500,
        "KIMacceleration": 10000,
        "KIMjogmode": 1000,
        "KIMvoltage": 20,
    },
    "Stamp Stage Y-Axis": {
        "KIMstep": 500,
        "KIMrate": 500,
        "KIMacceleration": 10000,
        "KIMjogmode": 1000,
        "KIMvoltage": 20,
    },
    "Stamp Stage Z-Axis": {
        "KIMstep": 500,
        "KIMrate": 500,
        "KIMacceleration": 10000,
        "KIMjogmode": 1000,
        "KIMvoltage": 20,
    }
}

# Define button-trigger to device-command mapping
""" The typical form of one mapping is {x: [(m, n)]}, where x, y and z are integers.
    It means when button No.x is pressed, trigger the command No.n in joystick_state to device No.m. """
button_trigger_device_command_mapping = {6: [(7, 1)],
                                         7: [(8, 0)],
                                         9: [(7, 2)],
                                         1: [(4, 11)],
                                         3: [(4, 12)],
                                         0: [(5, 11)],
                                         2: [(5, 12)]
                                         }

# Define button-hold to device-command mapping
""" The typical form of one mapping is {x: [(m, n, p)]}, where x, y and z are integers.
    It means when button No.x is pressed, continuously calling the command No.n in joystick_state to device No.m;
    when button No.x is released, trigger the command No.p in joystick_state to device No.m. """
button_hold_device_command_mapping = {5: [(0, 3, 2)],
                                      4: [(0, 4, 2)]
                                      }

# Define hat to device-command mapping
""" The typical form of one mapping is {(x, y): [(m, n)]}, where x, y are in {-1, 0, 1} and m, n are integers.
    It means when hat No.0 is pressed as (x, y), trigger the command No.n in joystick_state to device No.m. """
hat_device_command_mapping = {(1, 0): [(1, 3)],
                              (-1, 0): [(1, 4)],
                              (0, 1): [(2, 3)],
                              (0, -1): [(2, 4)],
                              (1, 1): [(1, 3), (2, 3)],
                              (1, -1): [(1, 3), (2, 4)],
                              (-1, 1): [(1, 4), (2, 3)],
                              (-1, -1): [(1, 4), (2, 4)]
                              }

# Define axis to device-command mapping
""" The typical form of one mapping is {x: [(m, n)]}, where x, y and z are integers.
    It means when the value of axis No.x is read, trigger the command No.n in joystick_state to device No.m. """
axis_device_command_mapping = {0: [(1, 5)],
                               1: [(2, 5)],
                               4: [(3, 7)]
                               }


# Class to initiate and start the joystick thread
class Controller:
    def __init__(self, devices, joystick):
        self.devices = devices
        self.joystick = joystick

    def start(self):
        # Start separate threads for the joystick
        joystick_thread = Thread(target=self.joystick.run)
        joystick_thread.start()


# Joystick class
class Joystick:
    def __init__(self, devices, device_name):
        self.devices = devices
        self.device_name = device_name
        self.device_CCdriver = DeviceCCDriver()
        self.last_moved_device = None  # This will store the last moved device
        self.last_disconnected_device = None  # This will store the last disconnected device

        # Initiate the null joystick_state for each device
        for device in device_name:
            joystick_state[device] = [False] * 13

    # Running function

    def run(self):
        joystick_loop_thread = Thread(target=self.joystick_loop)
        poll_joystick_state_thread = Thread(target=self.poll_joystick_state)

        joystick_loop_thread.start()
        poll_joystick_state_thread.start()

    # Joystick thread function
    """ In this function, the thread for joystick is being constructed.
        It continuously check the joystick events through pygame and manage these events into commands for hardware motions. """

    def joystick_loop(self):
        pygame.init()
        # logging.info('joystick connected successfully')
        print('joystick connected successfully')

        # Initialize the joystick
        if pygame.joystick.get_count() > 0:
            # Continue initialization as in your version
            joystick = pygame.joystick.Joystick(0)
            joystick.init()

            # Receive the hardware information on this joystick
            buttons = [f"Button {i}" for i in range(joystick.get_numbuttons())]
            hats = [f"Hat {i}" for i in range(joystick.get_numhats())]
            balls = [f"Ball {i}" for i in range(joystick.get_numballs())]
            axes = [f"Axis {i}" for i in range(joystick.get_numaxes())]

            # logging.info("Connected buttons:", buttons)
            # logging.info("Connected hats:", hats)
            # logging.info("Connected balls:", balls)
            # logging.info("Connected axes:", axes)

            print("Connected buttons:", buttons)
            print("Connected hats:", hats)
            print("Connected balls:", balls)
            print("Connected axes:", axes)

            # Main loop to get real-time joystick activity
            try:
                while True:
                    event = pygame.event.poll()

                    # Check each button
                    if event.type == pygame.JOYBUTTONDOWN:
                        # Use the button-device-command mapping for trigger
                        if event.button in button_trigger_device_command_mapping:
                            for device_index, command_index in button_trigger_device_command_mapping[event.button]:
                                if device_index < len(self.device_name):
                                    device = self.device_name[device_index]

                                    joystick_state[device][command_index] = True
                        # Use the button-device-command mapping for hold
                        if event.button in button_hold_device_command_mapping:
                            for device_index, hold_command_index, release_command_index in \
                            button_hold_device_command_mapping[event.button]:
                                # Execute the command continuously while the button is being pressed
                                while joystick.get_button(event.button):
                                    if device_index < len(self.device_name):
                                        device = self.device_name[device_index]
                                        joystick_state[device][hold_command_index] = True
                                    # Call your command function here
                                    pygame.event.pump()  # Update event stack

                    # Use the button-device-command mapping for release
                    if event.type == pygame.JOYBUTTONUP:
                        if event.button in button_hold_device_command_mapping:
                            for device_index, hold_command_index, release_command_index in \
                            button_hold_device_command_mapping[event.button]:
                                if device_index < len(self.device_name):
                                    device = self.device_name[device_index]
                                    joystick_state[device][hold_command_index] = False
                                    joystick_state[device][release_command_index] = False

                    # Check each hat
                    if event.type == pygame.JOYHATMOTION:
                        # Use the hat-device-command mapping
                        hat_value = joystick.get_hat(0)
                        if hat_value in hat_device_command_mapping:
                            for device_index, command_index in hat_device_command_mapping[hat_value]:
                                if device_index < len(self.device_name):
                                    device = self.device_name[device_index]

                                    joystick_state[device][command_index] = True

                    # Check each axis
                    for i in range(joystick.get_numaxes()):
                        axis = joystick.get_axis(i)

                        # For stamp stage
                        if i in {2, 3}:
                            process_axis(self.device_name, i, axis, joystick_state, axis_device_command_mapping, 10)

                        # For microscope
                        elif i == 4:
                            # axis = -axis if i == 4 else axis + 1
                            process_axis(self.device_name, i, axis, joystick_state, axis_device_command_mapping, 8)

                        # For other cases
                        else:
                            if i == 1:
                                axis = -axis  # Reverse axis-1
                            process_axis(self.device_name, i, axis, joystick_state, axis_device_command_mapping, 6)

                    # Prevent the loop from running too quickly and overwhelming the system
                    # time.sleep(0.01)

            # Quitting function
            except KeyboardInterrupt:
                # logging.info("Quitting...")
                print("Quitting...")
                pygame.quit()

    def stop(self):  # Add a stop method to set the flag
        self.gui_alive = False

    # Main function to convert joystick_state commands into real hardware motion
    """ This function continuoustly check the joystick_state for each device. 
        Once one state is read as 'True', the corresponding command is triggered. """

    def poll_joystick_state(self):
        global parameters

        while True:
            for device_name in self.device_name:  # Iterate over each device
                # print(joystick_state[device_name])
                if joystick_state[device_name][0]:
                    self.connect_device(self.last_disconnected_device)  # Connect last disconnected device
                if joystick_state[device_name][1]:
                    self.disconnect_device(self.last_moved_device)  # Disconnect last moved device
                if joystick_state[device_name][2]:
                    self.stop_device(self.last_moved_device)  # Stop last moved device
                if joystick_state[device_name][3]:
                    self.move_CCdevice(device_name, True)  # Move forward sample stage
                if joystick_state[device_name][4]:
                    self.move_CCdevice(device_name, False)  # Move reverse sample stage
                if joystick_state[device_name][5]:
                    direction, step = joystick_state[device_name][6]  # Store (direction, velocity) for sample stage motion
                    parameters[device_name]["CCstep"] += step
                    if direction == 'right':
                        self.move_CCdevice(device_name, True)  # Continuous move forward sample stage
                    if direction == 'left':
                        self.move_CCdevice(device_name, False)  # Continuous move reverse sample stage
                    parameters[device_name]["CCstep"] = 500
                if joystick_state[device_name][7]:
                    direction, step = joystick_state[device_name][8]  # Store (direction, velocity) for microscope motion
                    parameters[device_name]["CCstep"] += step
                    if direction == 'right':
                        self.move_CCdevice(device_name, True)  # Continuous move forward microscope
                    if direction == 'left':
                        self.move_CCdevice(device_name, False)  # Continuous move reverse microscope
                    parameters[device_name]["CCstep"] = 500
                if joystick_state[device_name][9]:
                    direction, velocity = joystick_state[device_name][10]  # Store (direction, velocity) for stamp stage motion
                    parameters[device_name]["KIMrate"] += velocity
                    if direction == 'right':
                        self.move_KIMdevice(device_name, True)  # Continuous move forward stamp stage
                    if direction == 'left':
                        self.move_KIMdevice(device_name, False)  # Continuous move reverse stamp stage
                    parameters[device_name]["KIMrate"] = 1000
                if joystick_state[device_name][11]:
                    self.move_KIMdevice(device_name, True)  # Move forward stamp stage
                if joystick_state[device_name][12]:
                    self.move_KIMdevice(device_name, False)  # Move reverse stamp stage

                # Reset joystick_state after checking
                joystick_state[device_name] = [False] * 13
            # Sleep for 0.01 ms
            time.sleep(0.01)

    # Function to obtain the device information
    """ Information including device_serial_num, device_type and device_channel.
        Special_device_name makes sure the two special cases: last_disconnected device and last_moved device. """

    def get_device_info(self, device_name, special_device_name):
        specific_device_name = special_device_name if device_name == special_device_name else device_name
        device_serial_num = next(
            (device.device_serial_num for device in self.devices if device.device_name == specific_device_name), None)
        device_type = next(
            (device.device_type for device in self.devices if device.device_name == specific_device_name), None)
        device_channel = next(
            (device.device_channel for device in self.devices if device.device_name == specific_device_name), None)
        return device_serial_num, device_type, device_channel

    # Implement connect_device, disconnect_device, stop_device, move_device, drive_device methods
    def connect_device(self, device_name):
        device_serial_num, device_type, device_channel = self.get_device_info(device_name,
                                                                              self.last_disconnected_device)
        if device_serial_num is not None:
            status_message = connect_device(device_serial_num, device_type, device_channel)
            print(status_message)
        else:
            print(f"No device found with name {device_name}")

    def disconnect_device(self, device_name):
        device_serial_num, device_type, device_channel = self.get_device_info(device_name, self.last_moved_device)
        if device_serial_num is not None:
            status_message = disconnect_device(device_serial_num, device_type, device_channel)
            print(status_message)
            self.last_disconnected_device = device_name
        else:
            print(f"No device found with name {device_name}")

    def stop_device(self, device_name):
        device_serial_num, device_type, device_channel = self.get_device_info(device_name, self.last_moved_device)
        if device_serial_num is not None:
            if device_channel is None:
                self.device_CCdriver.stop_drive()
            else:
                stop_device(device_serial_num, device_type, device_channel)
            status_message = stop_device(device_serial_num, device_type, device_channel)
            print(status_message)
        else:
            print(f"No device found with name {device_name}")

    def move_CCdevice(self, device_name, direction):
        global parameters

        device_serial_num, device_type, device_channel = self.get_device_info(device_name, device_name)

        if device_serial_num is not None:
            if device_name == 'Sample Stage Rotator':
                velocity = parameters[device_name]["CCvelocity"] * 10
                step = parameters[device_name]["CCstep"] * 10
            else:
                velocity = parameters[device_name]["CCvelocity"]
                step = parameters[device_name]["CCstep"]  # Use a default step for joystick control
            status_message = move_CCdevice(device_serial_num, device_type, device_channel, direction, step, velocity)
            print(status_message)
            self.last_moved_device = device_name
        else:
            print(f"No device found with name {device_name}")

    def drive_CCdevice(self, device_name, direction):
        global parameters

        device_serial_num, device_type, device_channel = self.get_device_info(device_name, device_name)

        if device_serial_num is not None:
            if device_name == 'Sample Stage Rotator':
                velocity = parameters[device_name]["CCvelocity"] * 10
                step = parameters[device_name]["CCstep"] * 10
            else:
                velocity = parameters[device_name]["CCvelocity"]
                step = parameters[device_name]["CCstep"]  # Use a default step for joystick control

        if device_serial_num is not None:
            status_message = self.device_driver.drive_device(device_serial_num, device_type, device_channel, direction,
                                                             step, velocity)
            print(status_message)
            self.last_moved_device = device_name
        else:
            print(f"No device found with name {device_name}")

    def move_KIMdevice(self, device_name, direction):
        global parameters

        device_serial_num, device_type, device_channel = self.get_device_info(device_name, device_name)

        step = parameters[device_name]["KIMstep"]
        rate = parameters[device_name]["KIMrate"]
        acceleration = parameters[device_name]["KIMacceleration"]
        mode = parameters[device_name]["KIMjogmode"]

        status_message = move_KIMdevice(device_serial_num, device_type, device_channel, direction, step,
                                        rate, acceleration, mode)
        print(status_message)
        self.last_moved_device = device_name

    def drive_KIMdevice(self, device_name, direction):
        global parameters

        device_serial_num, device_type, device_channel = self.get_device_info(device_name, device_name)

        voltage = parameters[device_name]["KIMvoltage"]
        rate = parameters[device_name]["KIMrate"]
        acceleration = parameters[device_name]["KIMacceleration"]

        if device_serial_num is not None:
            status_message = drive_KIMdevice(device_serial_num, device_type, device_channel, direction,
                                             voltage, rate, acceleration)
            print(status_message)
            self.last_moved_device = device_name
        else:
            print(f"No device found with name {device_name}")


# GUI class
class GUI:
    def __init__(self, master, device_name, device_serial_num, device_type, device_channel):
        self.master = master
        self.device_name = device_name
        self.device_serial_num = device_serial_num
        self.device_type = device_type
        self.device_channel = device_channel
        self.device_CCdriver = DeviceCCDriver()

        # Create a queue for real-time position reading
        self.stop_position_update_event = threading.Event()
        self.stop_event = threading.Event()
        self.position_queue = Queue()

        # Frame for each device within the main window
        self.frame = ttk.Frame(master, borderwidth=5, relief="solid")
        self.frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)  # Use grid instead of pack
        self.frame.configure(background='orange')

        self.status_label = tk.Label(self.frame, text="", bg='orange')
        self.status_label.grid(row=0, column=0, sticky='w')

        device_label = tk.Label(self.frame, text=device_name, bg='orange', font=('Helvetica', 16))
        device_label.grid(row=1, column=0, sticky='w')

        self.position_label = tk.Label(self.frame, text="", bg='orange')
        self.position_label.grid(row=2, column=0, sticky='w')

        # Button to connect and show/hide the choices
        self.show_hide_button = tk.Button(self.frame, text="Choices", command=self.show_hide_choices, bg='white')
        self.show_hide_button.grid(row=1, column=1, sticky='e')

        # This frame contains all other choices
        self.choices_frame = tk.Frame(self.frame, bg='orange')

        # Initialize all other controls inside choices_frame but initially hide them
        self.choices_frame.grid(row=0, column=2, rowspan=3, padx=20, sticky='ns')

        # Connect all devices initially
        self.connect_and_show_choices()

        # Buttons and labels inside choices_frame with custom colors and font
        button_properties = {'bg': 'white', 'activebackground': '#D0D0D0', 'font': ('Helvetica', 10)}
        label_properties = {'bg': 'gray', 'font': ('Helvetica', 10)}

        if device_channel is None:  # For CC devices

            self.step_label = tk.Label(self.choices_frame, text="Step", **label_properties)
            self.step_label.grid(row=0, column=5, pady=5)
            self.step_entry = tk.Entry(self.choices_frame, bg='white')
            self.step_entry.grid(row=0, column=6, pady=5)
            self.step_entry.insert(0, "100" if device_name == "Sample Stage Rotator" else "500")

            self.velocity_label = tk.Label(self.choices_frame, text="Velocity", **label_properties)
            self.velocity_label.grid(row=1, column=5, pady=5)
            self.velocity_entry = tk.Entry(self.choices_frame, bg='white')
            self.velocity_entry.grid(row=1, column=6, pady=5)
            self.velocity_entry.insert(0, "1000")

        else:  # For KIM devices
            self.step_label = tk.Label(self.choices_frame, text="Step", **label_properties)
            self.step_label.grid(row=0, column=5, pady=5)
            self.step_entry = tk.Entry(self.choices_frame, bg='white')
            self.step_entry.grid(row=0, column=6, pady=5)
            self.step_entry.insert(0, "1000")

            self.rate_label = tk.Label(self.choices_frame, text="Rate", **label_properties)
            self.rate_label.grid(row=1, column=5, pady=5)
            self.rate_entry = tk.Entry(self.choices_frame, bg='white')
            self.rate_entry.grid(row=1, column=6, pady=5)
            self.rate_entry.insert(0, "1000")

            self.acceleration_label = tk.Label(self.choices_frame, text="Acceleration", **label_properties)
            self.acceleration_label.grid(row=2, column=5, pady=5)
            self.acceleration_entry = tk.Entry(self.choices_frame, bg='white')
            self.acceleration_entry.grid(row=2, column=6, pady=5)
            self.acceleration_entry.insert(0, "10000")

            self.voltage_label = tk.Label(self.choices_frame, text="Voltage", **label_properties)
            self.voltage_label.grid(row=0, column=7, pady=5)
            self.voltage_entry = tk.Entry(self.choices_frame, bg='white')
            self.voltage_entry.grid(row=0, column=8, pady=5)
            self.voltage_entry.insert(0, "1000")

            self.jogmode_label = tk.Label(self.choices_frame, text="Mode", **label_properties)
            self.jogmode_label.grid(row=1, column=7, pady=5)
            self.jogmode_entry = tk.Entry(self.choices_frame, bg='white')
            self.jogmode_entry.grid(row=1, column=8, pady=5)
            self.jogmode_entry.insert(0, "2")

        connect_button = tk.Button(self.choices_frame, text="Connect", command=self.connect_device, **button_properties)
        connect_button.grid(row=0, column=0, pady=10)

        disconnect_button = tk.Button(self.choices_frame, text="Disconnect", command=self.disconnect_device,
                                      **button_properties)
        disconnect_button.grid(row=2, column=0, pady=10)

        home_button = tk.Button(self.choices_frame, text="Home", command=self.home_device, **button_properties)
        home_button.grid(row=1, column=2, pady=5)

        if device_channel is None:  # For CC devices

            drive_positive_button = tk.Button(self.choices_frame, text="Drive +",
                                              command=lambda: self.drive_CCdevice('right'),
                                              **button_properties)
            drive_positive_button.grid(row=0, column=2, pady=5)

            drive_negative_button = tk.Button(self.choices_frame, text="Drive -",
                                              command=lambda: self.drive_CCdevice('left'),
                                              **button_properties)
            drive_negative_button.grid(row=2, column=2, pady=5)

        else:  # For KIM devices

            drive_positive_button = tk.Button(self.choices_frame, text="Drive +",
                                              command=lambda: self.drive_KIMdevice('right'),
                                              **button_properties)
            drive_positive_button.grid(row=0, column=2, pady=5)

            drive_negative_button = tk.Button(self.choices_frame, text="Drive -",
                                              command=lambda: self.drive_KIMdevice('left'),
                                              **button_properties)
            drive_negative_button.grid(row=2, column=2, pady=5)

        stop_button = tk.Button(self.choices_frame, text="Stop", command=lambda: self.stop_device(),
                                **button_properties)
        stop_button.grid(row=1, column=4, pady=5)

        if device_channel is None:  # For CC devices

            if device_name != "Sample Stage Rotator":
                move_positive_button = tk.Button(self.choices_frame, text="Move +",
                                                 command=lambda: self.move_CCdevice(True),
                                                 **button_properties)
                move_positive_button.grid(row=0, column=4, pady=5)

                move_negative_button = tk.Button(self.choices_frame, text="Move -",
                                                 command=lambda: self.move_CCdevice(False),
                                                 **button_properties)
                move_negative_button.grid(row=2, column=4, pady=5)

            if device_name == "Sample Stage Rotator":
                rotate_positive_button = tk.Button(self.choices_frame, text="Rotate +",
                                                   command=lambda: self.move_CCdevice(True), **button_properties)
                rotate_positive_button.grid(row=0, column=4, pady=5)

                rotate_negative_button = tk.Button(self.choices_frame, text="Rotate -",
                                                   command=lambda: self.move_CCdevice(False), **button_properties)
                rotate_negative_button.grid(row=2, column=4, pady=5)

        else:  # For KIM devices

            move_positive_button = tk.Button(self.choices_frame, text="Move +",
                                             command=lambda: self.move_KIMdevice(True),
                                             **button_properties)
            move_positive_button.grid(row=0, column=4, pady=5)

            move_negative_button = tk.Button(self.choices_frame, text="Move -",
                                             command=lambda: self.move_KIMdevice(False),
                                             **button_properties)
            move_negative_button.grid(row=2, column=4, pady=5)

        apply_button = tk.Button(self.choices_frame, text="Apply Parameters", command=lambda: self.apply_parameters(),
                                 **button_properties)
        apply_button.grid(row=1, column=9, pady=5)

        self.choices_frame.grid_remove()  # Hide the frame initially

    # def get_current_device(self):
    #     return self.devices[self.current_device_index]

    # Implement connect_device, disconnect_device, stop_device, move_device, drive_device, update current position methods
    def connect_and_show_choices(self):
        self.connect_device()
        # Clear the stop event and start a new thread to update the position
        # self.stop_position_update_event.clear()
        # position_update_thread = threading.Thread(target=self.update_position_in_background)
        # position_update_thread.start()
        # self.update_position_label_from_queue()

    def show_hide_choices(self):
        if not self.choices_frame.winfo_ismapped():
            self.choices_frame.grid()
            self.show_hide_button.config(text="Hide")
        else:
            self.choices_frame.grid_remove()
            self.show_hide_button.config(text="Choices")

    def update_position_in_background(self):
        while not self.stop_position_update_event.is_set():
            connection_status, _ = is_connected(self.device_serial_num, self.device_type, self.device_channel)
            if connection_status:
                position = get_current_position(self.device_serial_num, self.device_type, self.device_channel)
                self.position_queue.put(position)
            time.sleep(0.1)  # Poll every 100 ms

    def update_position_label_from_queue(self):
        try:
            position = self.position_queue.get_nowait()
            self.position_label.config(text=f"{position}")
        except Empty:
            pass
        finally:
            if not self.stop_position_update_event.is_set():
                self.position_label.after(100, self.update_position_label_from_queue)

    def connect_device(self):
        status_message = connect_device(self.device_serial_num, self.device_type, self.device_channel)
        self.update_status(status_message)

    def disconnect_device(self):
        status_message = disconnect_device(self.device_serial_num, self.device_type, self.device_channel)
        self.update_status(status_message)

    def home_device(self):
        status_message = home_device(self.device_serial_num, self.device_type, self.device_channel)
        self.update_status(status_message)

    def move_CCdevice(self, direction):
        step = int(self.step_entry.get())
        velocity = int(self.velocity_entry.get())
        status_message = move_CCdevice(self.device_serial_num, self.device_type, self.device_channel, direction, step,
                                       velocity)
        self.update_status(status_message)

    def move_KIMdevice(self, direction):
        step = int(self.step_entry.get())
        rate = int(self.rate_entry.get())
        acceleration = int(self.acceleration_entry.get())
        mode = int(self.jogmode_entry.get())
        status_message = move_KIMdevice(self.device_serial_num, self.device_type, self.device_channel, direction, step,
                                        rate, acceleration, mode)
        self.update_status(status_message)

    def drive_CCdevice(self, direction):
        # velocity =
        # Start driving the device in a new thread
        step = int(self.step_entry.get())
        velocity = int(self.velocity_entry.get())
        status_message = self.device_CCdriver.start_drive(self.device_serial_num, self.device_type, self.device_channel,
                                                          direction, step, velocity)
        self.update_status(status_message)

    def drive_KIMdevice(self, direction):
        # velocity =
        # Start driving the device in a new thread
        voltage = int(self.voltage_entry.get())
        rate = int(self.rate_entry.get())
        acceleration = int(self.acceleration_entry.get())
        status_message = drive_KIMdevice(self.device_serial_num, self.device_type, self.device_channel, direction,
                                         voltage, rate, acceleration)
        self.update_status(status_message)

    def stop_device(self):
        # This will stop the 'drive_device' thread if it is running
        if self.device_channel is None:
            self.device_CCdriver.stop_drive()
        else:
            stop_device(self.device_serial_num, self.device_type, self.device_channel)

        # This will stop the movement of the device
        status_message = stop_device(self.device_serial_num, self.device_type, self.device_channel)
        self.update_status(status_message)
        # joystick_state[self.device_name][1] = False

    def update_position_label(self):
        if self.device_channel is None:
            connection_status, _ = is_connected(self.device_serial_num, self.device_type, self.device_channel)
            if not connection_status:
                self.position_label.config(text=f"Device {self.device_serial_num.value.decode()} is not connected.")
            else:
                position = get_current_position(self.device_serial_num, self.device_type, self.device_channel)
                self.position_label.config(text=f"{position}")
                self.position_label.after(100, self.update_position_label)
        else:
            connection_status, _ = is_connected(self.device_serial_num, self.device_type, self.device_channel)
            if not connection_status:
                self.position_label.config(
                    text=f"Device {self.device_serial_num.value.decode()} Channel {self.device_channel} is not connected.")
            else:
                position = get_current_position(self.device_serial_num, self.device_type, self.device_channel)
                self.position_label.config(text=f"{position}")
                self.position_label.after(100, self.update_position_label)

    def apply_parameters(self):

        global parameters

        if self.device_channel is None:

            parameters[self.device_name]["CCstep"] = float(self.step_entry.get())
            parameters[self.device_name]["CCvelocity"] = float(self.velocity_entry.get())

            status_message = set_CCstep(self.device_serial_num, self.device_type, self.device_channel,
                                        parameters[self.device_name]["CCstep"])
            self.update_status(status_message)

            set_CCvelocity(self.device_serial_num, self.device_type, self.device_channel,
                           parameters[self.device_name]["CCvelocity"])

            if status_message == f"Device {self.device_serial_num.value.decode()} is not connected.":
                messagebox.showinfo("Parameters", f"Parameters for {self.device_name} failed to be updated")
            else:
                messagebox.showinfo("Parameters", f"Parameters for {self.device_name} updated successfully")

        else:

            parameters[self.device_name]["KIMstep"] = float(self.step_entry.get())
            parameters[self.device_name]["KIMrate"] = float(self.rate_entry.get())
            parameters[self.device_name]["KIMacceleration"] = float(self.acceleration_entry.get())
            parameters[self.device_name]["KIMjogmode"] = float(self.jogmode_entry.get())
            parameters[self.device_name]["KIMvoltage"] = float(self.voltage_entry.get())

            status_message = set_KIMjog(self.device_serial_num, self.device_type, self.device_channel,
                                        parameters[self.device_name]["KIMjogmode"],
                                        parameters[self.device_name]["KIMstep"],
                                        parameters[self.device_name]["KIMstep"],
                                        parameters[self.device_name]["KIMrate"],
                                        parameters[self.device_name]["KIMacceleration"])
            self.update_status(status_message)

            if status_message == f"Device {self.device_serial_num.value.decode()} Channel {self.device_channel} is not connected.":
                messagebox.showinfo("Parameters",
                                    f"Parameters for {self.device_name} Channel {self.device_channel} failed to be updated")
            else:
                messagebox.showinfo("Parameters",
                                    f"Parameters for {self.device_name} Channel {self.device_channel} updated successfully")

    def update_status(self, message):
        self.master.after(0, self.status_label.config, {"text": message})