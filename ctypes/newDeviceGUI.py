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

# Global joystick state dictionary
joystick_state = {}
stop_flag = False  # Define stop_flag in the global scope
CURRENT_STEP = 50000  # initial step
CURRENT_VELOCITY = 1000  # initial velocity


class Controller:
    def __init__(self, devices, joystick):
        self.devices = devices
        self.joystick = joystick

    def start(self):
        # Start separate threads for the joystick and the GUI
        joystick_thread = Thread(target=self.joystick.run)
        joystick_thread.start()


class Joystick:
    def __init__(self, devices, device_name):
        self.devices = devices
        self.device_name = device_name
        self.device_driver = DeviceDriver()
        self.last_moved_device = None  # This will store the last moved device
        self.last_disconnected_device = None  # This will store the last disconnected device

        for device in device_name:
            joystick_state[device] = [False] * 9

    def run(self):
        joystick_loop_thread = Thread(target=self.joystick_loop)
        poll_joystick_state_thread = Thread(target=self.poll_joystick_state)

        joystick_loop_thread.start()
        poll_joystick_state_thread.start()

    def joystick_loop(self):
        pygame.init()
        print('joystick connected successfully')

        # Define button to device-command mapping
        button_device_command_mapping = {4: [(4, 1)],
                                         5: [(5, 0)],
                                         7: [(4, 2)]
                                         }

        # Define hat to device-command mapping
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
        def map_axis_to_velocity_stage(axis_value):
            STAGE_DEAD_ZONE = 0.1

            if abs(axis_value) < STAGE_DEAD_ZONE:
                return 0

            min_velocity = 0
            max_velocity = 1000
            velocity = min_velocity + (abs(axis_value)) * (max_velocity - min_velocity)
            return velocity

        def map_axis_to_velocity_scope(axis_value):
            SCOPE_DEAD_ZONE = 1.2

            if abs(axis_value) < SCOPE_DEAD_ZONE:
                return 0

            min_velocity = 0
            max_velocity = 1
            velocity = min_velocity + (abs(axis_value)) * (max_velocity - min_velocity)
            return velocity

        axis_device_command_mapping = {0: [(1, 5)],
                                       1: [(2, 5)],
                                       2: [(3, 5)],
                                       4: [(0, 7)],
                                       5: [(0, 7)]
                                       }

        # Initialize the first joystick
        if pygame.joystick.get_count() > 0:
            # Continue initialization as in your version
            joystick = pygame.joystick.Joystick(0)
            joystick.init()

            buttons = [f"Button {i}" for i in range(joystick.get_numbuttons())]
            hats = [f"Hat {i}" for i in range(joystick.get_numhats())]
            balls = [f"Ball {i}" for i in range(joystick.get_numballs())]
            axes = [f"Axis {i}" for i in range(joystick.get_numaxes())]

            print("Connected buttons:", buttons)
            print("Connected hats:", hats)
            print("Connected balls:", balls)
            print("Connected axes:", axes)

            # Main loop to get real-time joystick activity
            try:
                while True:
                    event = pygame.event.poll()
                    # device_name = self.last_moved_device

                    if event.type == pygame.JOYBUTTONDOWN:
                        # Use the button-device-command mapping
                        if event.button in button_device_command_mapping:
                            for device_index, command_index in button_device_command_mapping[event.button]:
                                if device_index < len(self.device_name):
                                    device = self.device_name[device_index]

                                    joystick_state[device][command_index] = True

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
                        if i != 4 and i != 5:
                            axis = joystick.get_axis(i)

                            if i == 1:
                                axis = -axis  # Reverse axis-1
                            if i == 4:
                                axis = -axis
                                axis = axis - 1
                            if i == 5:
                                axis = axis + 1
                            #
                            # if i == 4 or 5:
                            #     velocity = map_axis_to_velocity_scope(axis)  # Implement this function
                            # else:
                            velocity = map_axis_to_velocity_stage(axis)  # Implement this function

                            if velocity == 0:
                                continue
                            if axis < 0:
                                direction = 'left'
                            elif axis > 0:
                                direction = 'right'

                            if i in axis_device_command_mapping:
                                for device_index, command_index in axis_device_command_mapping[i]:
                                    if device_index < len(self.device_name):
                                        device = self.device_name[device_index]

                                        joystick_state[device][command_index] = True
                                        joystick_state[device][6] = [direction, velocity]
                        if i == 4 or i == 5:
                            axis = joystick.get_axis(i)
                            if i == 4:
                                axis = -axis
                                axis = axis - 1
                            if i == 5:
                                axis = axis + 1
                            #

                            velocity = map_axis_to_velocity_scope(axis)  # Implement this function

                            if velocity == 0:
                                continue
                            if axis < 0:
                                direction = 'left'
                            elif axis > 0:
                                direction = 'right'

                            if i in axis_device_command_mapping:
                                for device_index, command_index in axis_device_command_mapping[i]:
                                    if device_index < len(self.device_name):
                                        device = self.device_name[device_index]

                                        joystick_state[device][command_index] = True
                                        joystick_state[device][8] = [direction, velocity]
                    # Prevent the loop from running too quickly and overwhelming the system
                    time.sleep(0.01)

            except KeyboardInterrupt:
                print("Quitting...")
                pygame.quit()

    def stop(self):  # Add a stop method to set the flag
        self.gui_alive = False

    def poll_joystick_state(self):
        global CURRENT_VELOCITY
        while True:
            for device_name in self.device_name:  # iterate over each device
                # print(joystick_state[device_name])
                if joystick_state[device_name][0]:
                    self.connect_device(self.last_disconnected_device)  # pass device name to the method
                if joystick_state[device_name][1]:
                    self.disconnect_device(self.last_moved_device)
                if joystick_state[device_name][2]:
                    self.stop_device(self.last_moved_device)
                if joystick_state[device_name][3]:
                    self.move_device(device_name, True)
                if joystick_state[device_name][4]:
                    self.move_device(device_name, False)
                if joystick_state[device_name][5]:
                    direction, velocity = joystick_state[device_name][6]
                    CURRENT_VELOCITY += velocity
                    if direction == 'right':
                        self.move_device(device_name, True)
                    if direction == 'left':
                        self.move_device(device_name, False)
                if joystick_state[device_name][7]:
                    direction, velocity = joystick_state[device_name][8]
                    CURRENT_VELOCITY += velocity
                    if direction == 'right':
                        self.move_device(device_name, True)
                    if direction == 'left':
                        self.move_device(device_name, False)
                    # if direction == 'stop':
                    #     self.stop_device(device_name)

                # Reset button states after checking
                joystick_state[device_name] = [False] * 9
            time.sleep(0.01)

    # Implement connect_device, disconnect_device, stop_device, move_device, drive_device methods
    def connect_device(self, device_name):
        if device_name == "Last Disconnected Device":
            device_serial_num = self.last_disconnected_device
        else:
            device_serial_num = next(
                (device.device_serial_num for device in self.devices if device.device_name == device_name), None)
        if device_serial_num is not None:
            status_message = connect_device(device_serial_num)
            print(status_message)
        else:
            print(f"No device found with name {device_name}")

    def disconnect_device(self, device_name):
        if device_name == "Last Moved Device":
            device_serial_num = self.last_moved_device
        else:
            device_serial_num = next(
                (device.device_serial_num for device in self.devices if device.device_name == device_name), None)
        if device_serial_num is not None:
            status_message = disconnect_device(device_serial_num)
            print(status_message)
            self.last_disconnected_device = device_name
        else:
            print(f"No device found with name {device_name}")

    def stop_device(self, device_name):
        if device_name == "Last Disconnected Device":
            device_serial_num = self.last_moved_device
        else:
            device_serial_num = next(
                (device.device_serial_num for device in self.devices if device.device_name == device_name), None)
        if device_serial_num is not None:
            self.device_driver.stop_drive()
            status_message = stop_device(device_serial_num)
            print(status_message)
        else:
            print(f"No device found with name {device_name}")

    def move_device(self, device_name, direction):
        global CURRENT_STEP
        global CURRENT_VELOCITY

        device_serial_num = next(
            (device.device_serial_num for device in self.devices if device.device_name == device_name), None)

        if device_serial_num is not None:
            if device_name == 'Sample Stage Rotator':
                velocity = CURRENT_VELOCITY * 10
                step = CURRENT_STEP * 10
            else:
                velocity = CURRENT_VELOCITY
                step = CURRENT_STEP  # Use a default step for joystick control
            status_message = move_device(device_serial_num, direction, step, velocity)
            print(status_message)
            self.last_moved_device = device_name
        else:
            print(f"No device found with name {device_name}")

    def drive_device(self, device_name, direction):
        global CURRENT_STEP
        global CURRENT_VELOCITY

        device_serial_num = next(
            (device.device_serial_num for device in self.devices if device.device_name == device_name), None)

        if device_serial_num is not None:
            if device_name == 'Sample Stage Rotator':
                velocity = CURRENT_VELOCITY * 10
                step = CURRENT_STEP * 10
            else:
                velocity = CURRENT_VELOCITY
                step = CURRENT_STEP  # Use a default step for joystick control

        if device_serial_num is not None:
            status_message = self.device_driver.drive_device(device_serial_num, direction, step, velocity)
            print(status_message)
            self.last_moved_device = device_name
        else:
            print(f"No device found with name {device_name}")

class GUI:
    def __init__(self, master, device_name, device_serial_num):
        self.master = master
        self.device_name = device_name
        self.device_serial_num = device_serial_num
        self.device_driver = DeviceDriver()
        self.stop_position_update_event = threading.Event()
        self.stop_event = threading.Event()
        self.position_queue = Queue()

        # current_acceleration = get_current_acceleration(device_serial_num)

        # Frame for each device within the main window
        self.frame = ttk.Frame(master, borderwidth=5, relief="groove")
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

        self.connect_and_show_choices()

        # Buttons and labels inside choices_frame with custom colors and font
        button_properties = {'bg': 'white', 'activebackground': '#D0D0D0', 'font': ('Helvetica', 10)}
        label_properties = {'bg': 'white', 'font': ('Helvetica', 10)}

        self.step_entry = tk.Entry(self.choices_frame, bg='white')
        self.step_entry.grid(row=0, column=6, pady=5)
        self.step_entry.insert(0, "10" if device_name == "Sample Stage Rotator" else "50000")

        self.velocity_entry = tk.Entry(self.choices_frame, bg='white')
        self.velocity_entry.grid(row=1, column=6, pady=5)
        self.velocity_entry.insert(0, "1000")

        connect_button = tk.Button(self.choices_frame, text="Connect", command=self.connect_device, **button_properties)
        connect_button.grid(row=0, column=0, pady=10)

        disconnect_button = tk.Button(self.choices_frame, text="Disconnect", command=self.disconnect_device,
                                      **button_properties)
        disconnect_button.grid(row=2, column=0, pady=10)

        home_button = tk.Button(self.choices_frame, text="Home", command=self.home_device, **button_properties)
        home_button.grid(row=1, column=2, pady=5)

        drive_positive_button = tk.Button(self.choices_frame, text="Drive +",
                                          command=lambda: self.drive_device('right'),
                                          **button_properties)
        drive_positive_button.grid(row=0, column=2, pady=5)

        drive_negative_button = tk.Button(self.choices_frame, text="Drive -",
                                          command=lambda: self.drive_device('left'),
                                          **button_properties)
        drive_negative_button.grid(row=2, column=2, pady=5)

        stop_button = tk.Button(self.choices_frame, text="Stop", command=lambda: self.stop_device(),
                                **button_properties)
        stop_button.grid(row=1, column=4, pady=5)

        if device_name != "Sample Stage Rotator":
            move_positive_button = tk.Button(self.choices_frame, text="Move +", command=lambda: self.move_device(True),
                                             **button_properties)
            move_positive_button.grid(row=0, column=4, pady=5)

            move_negative_button = tk.Button(self.choices_frame, text="Move -", command=lambda: self.move_device(False),
                                             **button_properties)
            move_negative_button.grid(row=2, column=4, pady=5)

        if device_name == "Sample Stage Rotator":
            rotate_positive_button = tk.Button(self.choices_frame, text="Rotate +",
                                               command=lambda: self.move_device(True), **button_properties)
            rotate_positive_button.grid(row=0, column=4, pady=5)

            rotate_negative_button = tk.Button(self.choices_frame, text="Rotate -",
                                               command=lambda: self.move_device(False), **button_properties)
            rotate_negative_button.grid(row=2, column=4, pady=5)

        apply_button = tk.Button(self.choices_frame, text="Apply Parameters", command=lambda: self.apply_parameters(),
                                 **button_properties)
        apply_button.grid(row=1, column=8, pady=5)

        self.choices_frame.grid_remove()  # Hide the frame initially

    # def get_current_device(self):
    #     return self.devices[self.current_device_index]

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
            if lib.CC_Open(self.device_serial_num) == 0:
                position = get_current_position(self.device_serial_num)
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
        status_message = connect_device(self.device_serial_num)
        self.update_status(status_message)
        # joystick_state[self.device_name][0] = False

    def disconnect_device(self):
        status_message = disconnect_device(self.device_serial_num)
        self.update_status(status_message)

    def home_device(self):
        status_message = home_device(self.device_serial_num)
        self.update_status(status_message)
        # joystick_state[self.device_name][3] = False

    def move_device(self, direction):
        step = int(self.step_entry.get())
        velocity = int(self.velocity_entry.get())
        status_message = move_device(self.device_serial_num, direction, step, velocity)
        self.update_status(status_message)
        # if direction:
        #     joystick_state[self.device_name][3] = False
        # else:
        #     joystick_state[self.device_name][4] = False

    def drive_device(self, direction):
        # velocity =
        # Start driving the device in a new thread
        step = int(self.step_entry.get())
        velocity = int(self.velocity_entry.get())
        status_message = self.device_driver.start_drive(self.device_serial_num, direction, step, velocity)
        self.update_status(status_message)

    def stop_device(self):
        # This will stop the 'drive_device' thread if it is running
        self.device_driver.stop_drive()
        # This will stop the movement of the device
        status_message = stop_device(self.device_serial_num)
        self.update_status(status_message)
        # joystick_state[self.device_name][1] = False

    def update_position_label(self):
        if lib.CC_Open(self.device_serial_num) != 0:
            self.position_label.config(text="Device not connected")
        if lib.CC_Open(self.device_serial_num) == 0:
            position = get_current_position(self.device_serial_num)
            self.position_label.config(text=f"{position}")
            self.position_label.after(100, self.update_position_label)

    def apply_parameters(self):
        global CURRENT_STEP
        global CURRENT_VELOCITY

        CURRENT_STEP = float(self.step_entry.get())
        CURRENT_VELOCITY = float(self.velocity_entry.get())

        status_message = set_step(self.device_serial_num, CURRENT_STEP)
        self.update_status(status_message)

        set_velocity(self.device_serial_num, CURRENT_VELOCITY)

        if status_message == f"Device {self.device_serial_num.value.decode()} is not connected.":
            messagebox.showinfo("Parameters", f"Parameters failed to be updated")
        else:
            messagebox.showinfo("Parameters", f"Parameters updated successfully")

    def update_status(self, message):
        self.master.after(0, self.status_label.config, {"text": message})