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

# Global joystick state dictionary
joystick_state = {}
stop_flag = False  # Define stop_flag in the global scope

class Controller:
    def __init__(self, devices, joystick_gui):
        self.devices = devices
        self.device_driver = DeviceDriver()
        self.current_device_index = 0

        self.joystick_gui = joystick_gui  # Keep a reference to the joystick GUI

        self.gui_alive = True  # Add a flag here to track the GUI state

    def get_current_device(self):
        return self.devices[self.current_device_index]

    def cycle_devices(self):
        self.current_device_index = (self.current_device_index + 1) % len(self.devices)

    def dycle_devices(self):
        self.current_device_index = (self.current_device_index - 1) % len(self.devices)
    
    def joystick_loop(self):
        pygame.init()
        # Instead of printing, insert text into the joystick_info widget
        self.joystick_gui.joystick_info.delete(1.0, tk.END)
        self.joystick_gui.joystick_info.insert(tk.END, "Joystick connected successfully\n")
        self.joystick_gui.joystick_info.see(tk.END)

        # Define button to device-command mapping
        button_device_command_mapping = {0: (2, 1),
                                         3: (2, 0),
                                         4: (1, 1),
                                         5: (1, 0)
                                         }

        # Define hat to device-command mapping
        hat_device_command_mapping = {(1, 0): [(0, 3)],
                                      (-1, 0): [(0, 4)],
                                      (0, 1): [(0, 3)],
                                      (0, -1): [(0, 4)],
                                      (1, 1): [(0, 3), (0, 3)],
                                      (1, -1): [(0, 3), (0, 4)],
                                      (-1, 1): [(0, 4), (0, 3)],
                                      (-1, -1): [(0, 4), (0, 4)]
                                      }
        
        # Define axis to device-command mapping
        def map_axis_to_velocity(axis_value):
            min_velocity = -100
            max_velocity = 100
            velocity = min_velocity + (axis_value + 1) * (max_velocity - min_velocity) / 2
            return velocity


        # Wait for a joystick
        # get root window from joystick_gui
        root = self.joystick_gui.frame.winfo_toplevel()

        while self.gui_alive and pygame.joystick.get_count() == 0:
            # Check if root is alive before updating GUI
            if root.winfo_exists():
                self.joystick_gui.joystick_info.delete(1.0, tk.END)
                self.joystick_gui.joystick_info.insert(tk.END, 'Please connect a joystick...\n')
                self.joystick_gui.joystick_info.see(tk.END)
            else:
                # Break the loop if GUI is closed
                break
            time.sleep(10)
            pygame.joystick.quit()
            pygame.joystick.init()

        # Initialize the first joystick
        if pygame.joystick.get_count() > 0:
            # Initialize the first joystick
            joystick = pygame.joystick.Joystick(0)
            joystick.init()

            # List of buttons, hats, balls
            buttons = [f"Button {i}" for i in range(joystick.get_numbuttons())]
            hats = [f"Hat {i}" for i in range(joystick.get_numhats())]
            balls = [f"Ball {i}" for i in range(joystick.get_numballs())]
            axes = [f"Axis {i}" for i in range(joystick.get_numaxes())]

            print("Connected buttons:", buttons)
            print("Connected hats:", hats)
            print("Connected balls:", balls)
            print("Connected axes:", axes)

            self.joystick_gui.update_joystick_info(buttons, hats, balls, axes)

            # Main loop to get real time joystick activity
            try:
                while True:
                    # pump the event queue
                    pygame.event.pump()

                    # check each button
                    for i in range(joystick.get_numbuttons()):
                        # if button is pressed
                        if joystick.get_button(i):
                            print(f"Button {i} pressed.")
                            self.joystick_gui.update_button_pressed(i)

                    # check each hat
                    for i in range(joystick.get_numhats()):
                        hat = joystick.get_hat(i)
                        if hat != (0, 0):
                            print(f"Hat {i} moved: {hat}")
                            self.joystick_gui.update_hat_moved(i, hat)
                            # check if hat 0 is moved to (1,-1)
                            if i == 0 and hat == (1, 0):
                                self.cycle_devices()
                            if i == 0 and hat == (-1, 0):
                                self.dycle_devices()

                    # check each ball
                    for i in range(joystick.get_numballs()):
                        ball = joystick.get_ball(i)
                        if ball != (0, 0):
                            print(f"Ball {i} moved: {ball}")
                            self.joystick_gui.update_ball_moved(i, ball)

                    # check each axis
                    # for i in range(joystick.get_numaxes()):
                    #     axis = joystick.get_axis(i)
                    #     print(f"Axis {i} value: {axis:>6.3f}")
                    #     self.joystick_gui.update_axis_moved(i, axis)
                    #     time.sleep(0.2)

                    event = pygame.event.poll()
                    # device_name = self.last_moved_device

                    # if event.type == pygame.JOYBUTTONDOWN:
                    #     # Use the button-device-command mapping
                    #     if event.button == 4:
                    #         joystick_state[device_name][1] = True
                    #     if event.button == 5:
                    #         joystick_state[device_name][0] = True
                    #     if event.button == 7:
                    #         joystick_state[device_name][2] = True


                    if event.type == pygame.JOYHATMOTION:
                        # Use the hat-device-command mapping
                        hat_value = joystick.get_hat(0)
                        if hat_value in hat_device_command_mapping:
                            for device_index, command_index in hat_device_command_mapping[hat_value]:
                                if device_index < len(self.devices):
                                    device = self.devices[device_index]
                                    joystick_state[device.device_name][command_index] = True

                    
                    # JOYAXISMOTION event handler
                    if event.type == pygame.JOYAXISMOTION:
                        # Get the axis value and map to velocity
                        axis_value = joystick.get_axis(0)
                        velocity = map_axis_to_velocity(axis_value)
                        if axis_value < 0:
                            direction = 'left'
                        elif axis_value > 0:
                            direction = 'right'
                        else:
                            direction = 'stop'
                        if self.current_device_index < len(self.devices):
                            device_name = self.devices[self.current_device_index].device_name
                            # Update the joystick state for the device
                            joystick_state[device_name][5] = True
                            joystick_state[device_name][6] = [direction, velocity]


                    # prevent the loop from running too quickly and overwhelming the system
                    time.sleep(0.01)
            except KeyboardInterrupt:
                print("Quitting...")
                pygame.quit()

    def stop(self):  # Add a stop method to set the flag
        self.gui_alive = False


class JoystickGUI:
    def __init__(self, master):
        # Create frame for joystick
        self.frame = tk.Frame(master, borderwidth=5, relief="groove")
        self.frame.grid(row=4, column=0, sticky='nsew', padx=10, pady=10)  # Use grid instead of pack
        self.frame.configure(background='orange')

        # Add text widget for joystick info
        self.joystick_info = tk.Text(self.frame, height=5, width=5)
        self.joystick_info.grid(row=8, column=0, sticky='nsew')  # Change here from pack to grid

        joystick_label = tk.Label(self.frame, text="Joystick", bg='orange', font=('Helvetica', 16))
        joystick_label.grid(row=0, column=0, sticky='w')

        self.connected_buttons_label = tk.Label(self.frame, text="", bg='orange', wraplength=400)
        self.connected_buttons_label.grid(row=1, column=0, rowspan=2, sticky='we')

        self.connected_hats_label = tk.Label(self.frame, text="", bg='orange')
        self.connected_hats_label.grid(row=3, column=0, sticky='w')

        self.connected_balls_label = tk.Label(self.frame, text="", bg='orange')
        self.connected_balls_label.grid(row=4, column=0, sticky='w')

        self.connected_axes_label = tk.Label(self.frame, text="", bg='orange')
        self.connected_axes_label.grid(row=5, column=0, sticky='w')

        self.button_pressed_label = tk.Label(self.frame, text="", bg='orange')
        self.button_pressed_label.grid(row=6, column=0, sticky='w')

        self.hat_moved_label = tk.Label(self.frame, text="", bg='orange')
        self.hat_moved_label.grid(row=7, column=0, sticky='w')

        self.ball_moved_label = tk.Label(self.frame, text="", bg='orange')
        self.ball_moved_label.grid(row=8, column=0, sticky='w')

        self.axis_moved_label = tk.Label(self.frame, text="", bg='orange')
        self.axis_moved_label.grid(row=9, column=0, sticky='w')

    def update_joystick_info(self, buttons, hats, balls, axes):
        self.connected_buttons_label.config(text=f"Connected buttons: {buttons}")
        self.connected_hats_label.config(text=f"Connected hats: {hats}")
        self.connected_balls_label.config(text=f"Connected balls: {balls}")
        self.connected_axes_label.config(text=f"Connected axes: {axes}")

    def update_button_pressed(self, button_index):
        self.button_pressed_label.config(text=f"Button {button_index} pressed")

    def update_hat_moved(self, hat_index, hat_position):
        self.hat_moved_label.config(text=f"Hat {hat_index} moved: {hat_position}")

    def update_ball_moved(self, ball_index, ball_position):
        self.ball_moved_label.config(text=f"Ball {ball_index} moved: {ball_position}")

    def update_axis_moved(self, axis_index, axis_position):
        self.axis_moved_label.config(text=f"Axis {axis_index} moved: {axis_position}")


class DeviceGUI:
    def __init__(self, master, device_name, device_serial_num):
        self.master = master
        self.device_name = device_name
        self.device_serial_num = device_serial_num
        self.device_driver = DeviceDriver()
        self.stop_position_update_event = threading.Event()
        self.position_queue = Queue()

        # current_acceleration = get_current_acceleration(device_serial_num)

        # Initialize joystick_state for this device
        joystick_state[device_name] = [False] * 7

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

        disconnect_button = tk.Button(self.choices_frame, text="Disconnect", command=self.disconnect_device, **button_properties)
        disconnect_button.grid(row=2, column=0, pady=10)

        home_button = tk.Button(self.choices_frame, text="Home", command=self.home_device, **button_properties)
        home_button.grid(row=1, column=2, pady=5)

        current_velocity = int(self.velocity_entry.get())

        drive_positive_button = tk.Button(self.choices_frame, text="Drive +", command=lambda: self.drive_device('right', current_velocity),
                                          **button_properties)
        drive_positive_button.grid(row=0, column=2, pady=5)

        drive_negative_button = tk.Button(self.choices_frame, text="Drive -", command=lambda: self.drive_device('left', current_velocity),
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

        #
        # self.acceleration_entry = tk.Entry(self.choices_frame, bg='white')
        # self.acceleration_entry.grid(row=2, column=6, pady=5)
        # self.acceleration_entry.insert(0, "10000")

        self.choices_frame.grid_remove()  # Hide the frame initially
    
    # def get_current_device(self):
    #     return self.devices[self.current_device_index]


    def connect_and_show_choices(self):
        self.connect_device()
        # Clear the stop event and start a new thread to update the position
        self.stop_position_update_event.clear()
        position_update_thread = threading.Thread(target=self.update_position_in_background)
        position_update_thread.start()
        self.update_position_label_from_queue()

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
                
    def poll_joystick_state(self):
        while True:
            # time.sleep(1)
            # print(joystick_state[self.device_name])
            if joystick_state[self.device_name][0]:
                self.connect_device()
                # self.last_command_device = (self.get_current_device().device_name, 'connect')
            if joystick_state[self.device_name][1]:
                self.disconnect_device()
                # self.last_command_device = (self.get_current_device().device_name, 'disconnect')
            if joystick_state[self.device_name][2]:
                self.stop_device()
                # self.last_command_device = (self.get_current_device().device_name, 'stop')
        
            if joystick_state[self.device_name][3]:
                self.move_device(True)
                # self.last_command_device = (self.get_current_device().device_name, 'move_true')
            if joystick_state[self.device_name][4]:
                self.move_device(False)
                # self.last_command_device = (self.get_current_device().device_name, 'move_false')
            if joystick_state[self.device_name][5]:
                direction, velocity = joystick_state[self.device_name][6]
                self.drive_device(direction, velocity)
                # self.devices[self.current_device_index].start_drive(self.devices[self.current_device_index].device_serial_num, direction, velocity)
                # self.last_command_device = (self.get_current_device().device_name, f'drive_{direction}')

            # Reset button states after checking
            joystick_state[self.device_name] = [False] * 7
            time.sleep(0.01)


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
        status_message = move_device(self.device_serial_num, direction, step)
        self.update_status(status_message)
        if direction:
            joystick_state[self.device_name][3] = False
        else:
            joystick_state[self.device_name][4] = False

    def drive_device(self, direction, velocity):
        # velocity = 
        # Start driving the device in a new thread
        status_message = DeviceDriver.drive_device(self, self.device_serial_num, direction, velocity)
        self.device_driver.start_drive(self.device_serial_num, direction, velocity)
        self.update_status(status_message)
        # if direction:
        #     joystick_state[self.device_name][4] = False
        # else:
        #     joystick_state[self.device_name][5] = False
        joystick_state[self.device_name][5] = False

    def rotate_device(self, direction):
        rotation_amount = int(self.step_entry.get())
        status_message = move_device(self.device_serial_num, direction, rotation_amount)
        self.update_status(status_message)

    def stop_device(self):
        # This will stop the 'drive_device' thread if it is running
        self.device_driver.stop_drive()
        # This will stop the movement of the device
        status_message = stop_device(self.device_serial_num)
        self.update_status(status_message)
        joystick_state[self.device_name][1] = False

    def update_position_label(self):
        if lib.CC_Open(self.device_serial_num) != 0:
            self.position_label.config(text="Device not connected")
        if lib.CC_Open(self.device_serial_num) == 0:
            position = get_current_position(self.device_serial_num)
            self.position_label.config(text=f"{position}")
            self.position_label.after(100, self.update_position_label)

    def apply_parameters(self):
        step = float(self.step_entry.get())
        velocity = float(self.velocity_entry.get())
        # acceleration = float(self.acceleration_entry.get())

        set_step(self.device_serial_num, step)
        set_velocity(self.device_serial_num, velocity)
        # set_acceleration(self.device_serial_num, acceleration)

        messagebox.showinfo("Parameters", f"Parameters updated successfully")

    def update_status(self, message):
        self.status_label.config(text=message)