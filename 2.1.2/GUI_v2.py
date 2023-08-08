import pygame
from threading import Thread
import globals
from position import *
from connectivity import *
from movement import *
from camera_v2 import main as camera_main, get_polygon, get_shift, get_angle, zoom_in_camera, \
    zoom_out_camera, capture_frame
import time
from queue import Queue, Empty
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, QGridLayout, QWidget, QFrame, \
    QMessageBox, QCheckBox, QVBoxLayout
from PyQt5.QtGui import QFont, QDoubleValidator, QPixmap
from PyQt5.QtCore import Qt
import json


# These two functions process the real-time value of an axis on the joystick to a continuous motion command
def map_axis_to_step(axis, axis_value):
    # Microscope
    if axis == 4:
        DEAD_ZONE = 0.3
        max_step = 100
    # Stamp stage
    if axis == 2 or 3:
        DEAD_ZONE = 0.1
        max_step = 10
    # Sample stage
    else:
        DEAD_ZONE = 0.1
        max_step = 1000

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

# Initial global parameters for all devices
parameters = {
    "Microscope": {
        "CCstep": 500,
        "CCvelocity": 1000,
    },
    "Sample Stage X-Axis": {
        "CCstep": 500,
        "CCvelocity": 1000,
        "small_step_size": 500,
    },
    "Sample Stage Y-Axis": {
        "CCstep": 500,
        "CCvelocity": 1000,
        "small_step_size": 500,
    },
    "Sample Stage Rotator": {
        "CCstep": 1000,
        "CCvelocity": 1000,
        "small_angle_size": 1000
    },
    "Stamp Stage X-Axis": {
        "KIMstep": 1000,
        "KIMrate": 1000,
        "KIMacceleration": 10000,
        "KIMjogmode": 2,
        "KIMvoltage": 1000,
    },
    "Stamp Stage Y-Axis": {
        "KIMstep": 1000,
        "KIMrate": 1000,
        "KIMacceleration": 10000,
        "KIMjogmode": 2,
        "KIMvoltage": 1000,
    },
    "Stamp Stage Z-Axis": {
        "KIMstep": 1000,
        "KIMrate": 1000,
        "KIMacceleration": 10000,
        "KIMjogmode": 2,
        "KIMvoltage": 1000,
    },
    "Camera": {
        "Rescale": (25580, 19060),
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
                    time.sleep(0.001)

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
                    direction, velocity = joystick_state[device_name][
                        6]  # Store (direction, velocity) for sample stage motion
                    parameters[device_name]["CCvelocity"] += velocity
                    if direction == 'right':
                        self.move_CCdevice(device_name, True)  # Continuous move forward sample stage
                    if direction == 'left':
                        self.move_CCdevice(device_name, False)  # Continuous move reverse sample stage
                    # parameters[device_name]["CCstep"] -= step
                if joystick_state[device_name][7]:
                    direction, velocity = joystick_state[device_name][
                        8]  # Store (direction, velocity) for microscope motion
                    parameters[device_name]["CCstep"] += velocity
                    if direction == 'right':
                        self.move_CCdevice(device_name, True)  # Continuous move forward microscope
                    if direction == 'left':
                        self.move_CCdevice(device_name, False)  # Continuous move reverse microscope
                    # parameters[device_name]["CCstep"] -= step
                if joystick_state[device_name][9]:
                    direction, velocity = joystick_state[device_name][
                        10]  # Store (direction, velocity) for stamp stage motion
                    parameters[device_name]["KIMrate"] += velocity
                    if direction == 'right':
                        self.move_KIMdevice(device_name, True)  # Continuous move forward stamp stage
                    if direction == 'left':
                        self.move_KIMdevice(device_name, False)  # Continuous move reverse stamp stage
                    parameters[device_name]["KIMrate"] -= velocity
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
class GUI(QMainWindow):

    def __init__(self, device_name, device_serial_num, device_type, device_channel, device_profile):
        super().__init__()

        self.device_name = device_name
        self.device_serial_num = device_serial_num
        self.device_type = device_type
        self.device_channel = device_channel
        self.device_CCdriver = DeviceCCDriver()
        self.device_profile = device_profile

        # Create a queue for real-time position reading
        # self.stop_position_update_event = threading.Event()
        # self.stop_event = threading.Event()
        # self.position_queue = Queue()

        self.initGUI()

    def initGUI(self):
        self.setWindowTitle('Device GUI')
        self.setGeometry(100, 100, 800, 600)

        widget = QWidget(self)
        self.setCentralWidget(widget)

        grid = QGridLayout()
        widget.setLayout(grid)

        # Buttons and labels inside choices_frame with custom colors and font
        label_font = QFont("Arial", 10)
        label_font.setBold(True)

        button_font = QFont("Arial", 10)
        button_size = 50
        radius = button_size // 2

        # Create frames for special widgets: camera
        if self.device_type == "widget":

            # Camera label
            camera_label = QLabel(f"Basler Ace acA1920-40uc", self)
            font = QFont("Arial")
            font.setPointSize(12)  # Set the font size to 14 points
            camera_label.setFont(font)
            grid.addWidget(camera_label, 0, 0)

            # Camera status
            self.status_label = QLabel("Camera connected successfully.", self)
            font = QFont("Arial")
            font.setPointSize(12)  # Set the font size to 14 points
            self.status_label.setFont(font)
            grid.addWidget(self.status_label, 1, 0)

            # Open camera
            self.open_camera_button = QPushButton('Open Camera')
            self.open_camera_button.setFont(button_font)
            self.open_camera_button.setStyleSheet("background-color: HoneyDew;")
            self.open_camera_button.pressed.connect(self.open_camera)
            self.open_camera_button.setMinimumHeight(70)
            grid.addWidget(self.open_camera_button, 2, 0)

            # Capture screen
            self.capture_button = QPushButton('Capture')
            self.capture_button.setFont(button_font)
            self.capture_button.setStyleSheet("background-color: HoneyDew;")
            self.capture_button.pressed.connect(self.capture)
            self.capture_button.setMinimumHeight(70)
            grid.addWidget(self.capture_button, 3, 0, 1, 4)

            # Tracking mode
            tracker_widget = QWidget()
            tracker_layout = QVBoxLayout()
            self.tracker_image = QLabel()
            pixmap = QPixmap(r"d:\大三下\科研\codes\joystick-transfer\ctypes\2.1.2\tracker.png")
            self.tracker_image.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio))
            self.tracker_image.mousePressEvent = self.trigger_mode1
            tracker_layout.addWidget(self.tracker_image, alignment=Qt.AlignCenter)
            tracker_widget.setLayout(tracker_layout)
            grid.addWidget(tracker_widget, 0, 1)

            # Drawing mode
            pen_widget = QWidget()
            pen_layout = QVBoxLayout()
            self.pen_image = QLabel()
            pixmap = QPixmap(r"d:\大三下\科研\codes\joystick-transfer\ctypes\2.1.2\pen.png")
            self.pen_image.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio))
            self.pen_image.mousePressEvent = self.trigger_mode2
            pen_layout.addWidget(self.pen_image, alignment=Qt.AlignCenter)
            pen_widget.setLayout(pen_layout)
            grid.addWidget(pen_widget, 1, 1)

            # Measuring mode
            ruler_widget = QWidget()
            ruler_layout = QVBoxLayout()
            self.ruler_image = QLabel()
            pixmap = QPixmap(r"d:\大三下\科研\codes\joystick-transfer\ctypes\2.1.2\ruler.png")
            self.ruler_image.setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio))
            self.ruler_image.mousePressEvent = self.trigger_mode3
            ruler_layout.addWidget(self.ruler_image, alignment=Qt.AlignCenter)
            ruler_widget.setLayout(ruler_layout)
            grid.addWidget(ruler_widget, 2, 1)

            # Zoom in
            self.zoom_in_button = QPushButton('+')
            self.zoom_in_button.setFont(button_font)
            self.zoom_in_button.setFixedSize(button_size, button_size)
            self.zoom_in_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: Ivory;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: FireBrick;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.zoom_in_button.pressed.connect(self.zoom_in)
            grid.addWidget(self.zoom_in_button, 0, 4)

            # Zoom out
            self.zoom_out_button = QPushButton('-')
            self.zoom_out_button.setFont(button_font)
            self.zoom_out_button.setFixedSize(button_size, button_size)
            self.zoom_out_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: Ivory;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: LightGray;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.zoom_out_button.pressed.connect(self.zoom_out)
            grid.addWidget(self.zoom_out_button, 1, 4)

            # Fivefold Mirror
            self.fivefold_button = QPushButton('5X')
            self.fivefold_button.setFont(button_font)
            self.fivefold_button.setFixedSize(button_size, button_size)
            self.fivefold_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: Crimson;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: LightGray;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.fivefold_button.pressed.connect(self.fivefold)
            grid.addWidget(self.fivefold_button, 0, 2)

            # Tenfold Mirror
            self.tenfold_button = QPushButton('10X')
            self.tenfold_button.setFont(button_font)
            self.tenfold_button.setFixedSize(button_size, button_size)
            self.tenfold_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: Gold;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: GoldenRod;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.tenfold_button.pressed.connect(self.tenfold)
            grid.addWidget(self.tenfold_button, 1, 2)

            # Tenfold Mirror
            self.twentyfold_button = QPushButton('20X')
            self.twentyfold_button.setFont(button_font)
            self.twentyfold_button.setFixedSize(button_size, button_size)
            self.twentyfold_button.setStyleSheet((
                    "QPushButton {"
                    "    background-color: LawnGreen;"
                    "    border-radius: " + str(radius) + "px;"
                                                          "    width: " + str(button_size) + "px;"
                                                                                             "    height: " + str(
                button_size) + "px;"
                               "}"
                               "QPushButton:pressed {"
                               "    background-color: LimeGreen;"
                               "    border: 2px solid gray;"
                               "    border-radius: " + str(radius) + "px;"
                                                                     "}"
            ))
            self.twentyfold_button.pressed.connect(self.twentyfold)
            grid.addWidget(self.twentyfold_button, 2, 2)

            # Retrieve Polygon
            self.retrieve_polygon_button = QPushButton('Retrieve Flake')
            self.retrieve_polygon_button.setFont(button_font)
            self.retrieve_polygon_button.setStyleSheet("background-color: Ivory;")
            self.retrieve_polygon_button.pressed.connect(self.retrieve_polygon)
            grid.addWidget(self.retrieve_polygon_button, 0, 3)

            # Calibrate Polygon
            self.calibrate_button = QPushButton('Calibrate Flake')
            self.calibrate_button.pressed.connect(self.calibrate)
            self.calibrate_button.setFont(button_font)
            self.calibrate_button.setStyleSheet("background-color: Ivory;")
            grid.addWidget(self.calibrate_button, 1, 3)

            # Align Polygon
            self.align_button = QPushButton('Track Flake')
            self.align_button.pressed.connect(self.align)
            self.align_button.setFont(button_font)
            self.align_button.setStyleSheet("background-color: Ivory;")
            grid.addWidget(self.align_button, 2, 3)

            # Turn on/off alignment
            self.light_button = QPushButton()
            self.light_button.setCheckable(True)
            self.light_button.toggled.connect(self.light_action)
            self.light_button.setFont(button_font)
            self.light_button.setStyleSheet("""
                QPushButton {
                    background-color: red;
                    border-style: solid;
                    border-width: 15px;
                    border-radius: 25px;
                    min-width: 20px;
                    max-width: 20px;
                    min-height: 20px;
                    max-height: 20px;
                }
                QPushButton:checked {
                    background-color: green;
                }
            """)
            # create a layout and add the light_button to it
            light_button_layout = QVBoxLayout()
            light_button_layout.addWidget(self.light_button)
            # add the layout to the grid
            grid.addLayout(light_button_layout, 2, 4)


        # Create frames for devices
        else:

            # Device label
            if self.device_channel is None:  # For CC devices
                device_label = QLabel(f"Device KDC-{self.device_serial_num.value.decode()}", self)
            if self.device_channel is not None:  # For KIM devices
                device_label = QLabel(
                    f"Device KIM-{self.device_serial_num.value.decode()}-Channel {self.device_channel}",
                    self)
            font = QFont("Arial")
            font.setPointSize(8)
            device_label.setFont(font)
            grid.addWidget(device_label, 0, 0)

            # Device status
            self.status_label = QLabel("", self)
            font = QFont("Arial")
            font.setPointSize(12)
            self.status_label.setFont(font)
            grid.addWidget(self.status_label, 1, 0)

            # Device current position
            self.position_label = QLabel("", self)
            grid.addWidget(self.position_label, 2, 0)

            # Define a grid layout for the choices frame
            self.choices_frame = QFrame(self)
            grid.addWidget(self.choices_frame, 3, 0, 1, 2)

            choices_grid = QGridLayout(self.choices_frame)
            self.choices_frame.setLayout(choices_grid)
            self.choices_frame.hide()

            self.show_hide_button = QPushButton("Choices", self)
            self.show_hide_button.setFont(button_font)
            self.show_hide_button.setStyleSheet("background-color: silver;")
            grid.addWidget(self.show_hide_button, 1, 1)
            self.show_hide_button.clicked.connect(self.show_hide_choices)

            # Connect all devices initially
            self.connect_and_show_choices()

            if self.device_channel is None:  # For CC devices

                self.step_label = QLabel("Step", self.choices_frame)
                self.step_label.setFont(label_font)
                self.step_label.setStyleSheet("background-color: lightgray;")
                choices_grid.addWidget(self.step_label, 0, 5)

                self.step_entry = QLineEdit(self.choices_frame)
                self.step_entry.setValidator(QDoubleValidator())
                self.step_entry.setText("1000" if self.device_name == "Sample Stage Rotator" else "500")
                choices_grid.addWidget(self.step_entry, 0, 6)

                self.velocity_label = QLabel("Velocity", self.choices_frame)
                self.velocity_label.setFont(label_font)
                self.velocity_label.setStyleSheet("background-color: lightgray;")
                choices_grid.addWidget(self.velocity_label, 1, 5)

                self.velocity_entry = QLineEdit(self.choices_frame)
                self.velocity_entry.setValidator(QDoubleValidator())
                self.velocity_entry.setText("1000")
                choices_grid.addWidget(self.velocity_entry, 1, 6)

            else:  # For KIM devices
                # Coarse settings

                # Create a sub-frame inside the existing frame
                self.coarse_frame = QFrame(self.choices_frame)
                self.coarse_frame.setFrameShape(QFrame.StyledPanel)
                self.coarse_frame.setFrameShadow(QFrame.Raised)
                self.coarse_frame.setStyleSheet("border: 1px solid black;")

                # Grid layout for the sub-frame
                coarse_frame_grid = QGridLayout(self.coarse_frame)

                self.bigstep_label = QLabel("STEP", self.coarse_frame)
                self.bigstep_label.setFont(label_font)
                self.bigstep_label.setStyleSheet("background-color: lightgray;")
                coarse_frame_grid.addWidget(self.bigstep_label, 0, 0)

                self.bigstep_entry = QLineEdit(self.coarse_frame)
                self.bigstep_entry.setValidator(QDoubleValidator())
                self.bigstep_entry.setText("1000")
                coarse_frame_grid.addWidget(self.bigstep_entry, 0, 1)

                self.bigrate_label = QLabel("RATE", self.coarse_frame)
                self.bigrate_label.setFont(label_font)
                self.bigrate_label.setStyleSheet("background-color: lightgray;")
                coarse_frame_grid.addWidget(self.bigrate_label, 1, 0)

                self.bigrate_entry = QLineEdit(self.coarse_frame)
                self.bigrate_entry.setValidator(QDoubleValidator())
                self.bigrate_entry.setText("1000")
                coarse_frame_grid.addWidget(self.bigrate_entry, 1, 1)

                self.bigacceleration_label = QLabel("ACCE", self.coarse_frame)
                self.bigacceleration_label.setFont(label_font)
                self.bigacceleration_label.setStyleSheet("background-color: lightgray;")
                coarse_frame_grid.addWidget(self.bigacceleration_label, 0, 2)

                self.bigacceleration_entry = QLineEdit(self.coarse_frame)
                self.bigacceleration_entry.setValidator(QDoubleValidator())
                self.bigacceleration_entry.setText("10000")
                coarse_frame_grid.addWidget(self.bigacceleration_entry, 0, 3)

                self.bigvoltage_label = QLabel("VOLT", self.coarse_frame)
                self.bigvoltage_label.setFont(label_font)
                self.bigvoltage_label.setStyleSheet("background-color: lightgray;")
                coarse_frame_grid.addWidget(self.bigvoltage_label, 1, 2)

                self.bigvoltage_entry = QLineEdit(self.coarse_frame)
                self.bigvoltage_entry.setValidator(QDoubleValidator())
                self.bigvoltage_entry.setText("1000")
                coarse_frame_grid.addWidget(self.bigvoltage_entry, 1, 3)

                # Add the sub-frame to the existing grid layout
                choices_grid.addWidget(self.coarse_frame, 0, 5, 2, 5)  # Adjust grid position as needed

                # Fine settings

                # Create a sub-frame inside the existing frame
                self.fine_frame = QFrame(self.choices_frame)
                self.fine_frame.setFrameShape(QFrame.StyledPanel)
                self.fine_frame.setFrameShadow(QFrame.Raised)
                self.fine_frame.setStyleSheet("border: 1px solid black;")

                # Grid layout for the sub-frame
                fine_frame_grid = QGridLayout(self.fine_frame)

                self.smallstep_label = QLabel("step", self.fine_frame)
                self.smallstep_label.setFont(label_font)
                self.smallstep_label.setStyleSheet("background-color: lightgray;")
                fine_frame_grid.addWidget(self.smallstep_label, 0, 0)

                self.smallstep_entry = QLineEdit(self.fine_frame)
                self.smallstep_entry.setValidator(QDoubleValidator())
                self.smallstep_entry.setText("100")
                fine_frame_grid.addWidget(self.smallstep_entry, 0, 1)

                self.smallrate_label = QLabel("rate", self.fine_frame)
                self.smallrate_label.setFont(label_font)
                self.smallrate_label.setStyleSheet("background-color: lightgray;")
                fine_frame_grid.addWidget(self.smallrate_label, 1, 0)

                self.smallrate_entry = QLineEdit(self.fine_frame)
                self.smallrate_entry.setValidator(QDoubleValidator())
                self.smallrate_entry.setText("100")
                fine_frame_grid.addWidget(self.smallrate_entry, 1, 1)

                self.smallacceleration_label = QLabel("acce", self.fine_frame)
                self.smallacceleration_label.setFont(label_font)
                self.smallacceleration_label.setStyleSheet("background-color: lightgray;")
                fine_frame_grid.addWidget(self.smallacceleration_label, 0, 2)

                self.smallacceleration_entry = QLineEdit(self.fine_frame)
                self.smallacceleration_entry.setValidator(QDoubleValidator())
                self.smallacceleration_entry.setText("10000")
                fine_frame_grid.addWidget(self.smallacceleration_entry, 0, 3)

                self.smallvoltage_label = QLabel("volt", self.fine_frame)
                self.smallvoltage_label.setFont(label_font)
                self.smallvoltage_label.setStyleSheet("background-color: lightgray;")
                fine_frame_grid.addWidget(self.smallvoltage_label, 1, 2)

                self.smallvoltage_entry = QLineEdit(self.fine_frame)
                self.smallvoltage_entry.setValidator(QDoubleValidator())
                self.smallvoltage_entry.setText("1000")
                fine_frame_grid.addWidget(self.smallvoltage_entry, 1, 3)

                # Add the sub-frame to the existing grid layout
                choices_grid.addWidget(self.fine_frame, 0, 10, 2, 5)  # Adjust grid position as needed

                self.mode = "Jog"
                self.jogmode_button = QPushButton("Jog", self.choices_frame)
                self.jogmode_button.clicked.connect(self.switch_jogmode)
                # self.jogmode_button.resize(self.jogmode_button.sizeHint())
                # self.jogmode_button.move(50, 50)
                choices_grid.addWidget(self.jogmode_button, 1, 15)

            connect_button = QPushButton("Connect", self.choices_frame)
            connect_button.setFont(button_font)
            connect_button.setStyleSheet("background-color: HoneyDew;")
            connect_button.clicked.connect(self.connect_device)
            grid.addWidget(connect_button, 0, 1)

            disconnect_button = QPushButton("Disconnect", self.choices_frame)
            disconnect_button.setFont(button_font)
            disconnect_button.setStyleSheet("color: white; background-color: maroon;")
            disconnect_button.clicked.connect(self.disconnect_device)
            grid.addWidget(disconnect_button, 2, 1)

            home_button = QPushButton("Home", self.choices_frame)
            home_button.setFont(button_font)
            home_button.setStyleSheet("background-color: gold;")
            home_button.clicked.connect(self.home_device)
            choices_grid.addWidget(home_button, 1, 2)

            if self.device_channel is None:  # For CC devices
                drive_positive_button = QPushButton("Drive +", self.choices_frame)
                drive_positive_button.setFont(button_font)
                drive_positive_button.setStyleSheet("background-color: Ivory;")
                drive_positive_button.clicked.connect(lambda: self.drive_CCdevice('right'))
                choices_grid.addWidget(drive_positive_button, 0, 2)

                drive_negative_button = QPushButton("Drive -", self.choices_frame)
                drive_negative_button.setFont(button_font)
                drive_negative_button.setStyleSheet("background-color: Ivory;")
                drive_negative_button.clicked.connect(lambda: self.drive_CCdevice('left'))
                choices_grid.addWidget(drive_negative_button, 2, 2)

            else:  # For KIM devices
                drive_positive_button = QPushButton("Drive +", self.choices_frame)
                drive_positive_button.setFont(button_font)
                drive_positive_button.setStyleSheet("background-color: Ivory;")
                drive_positive_button.clicked.connect(lambda: self.drive_KIMdevice(True))
                choices_grid.addWidget(drive_positive_button, 0, 2)

                drive_negative_button = QPushButton("Drive -", self.choices_frame)
                drive_negative_button.setFont(button_font)
                drive_negative_button.setStyleSheet("background-color: Ivory;")
                drive_negative_button.clicked.connect(lambda: self.drive_KIMdevice(False))
                choices_grid.addWidget(drive_negative_button, 2, 2)

            stop_button = QPushButton("Stop", self.choices_frame)
            stop_button.setFont(button_font)
            stop_button.setStyleSheet("color: white; background-color: firebrick;")
            stop_button.clicked.connect(self.stop_device)
            choices_grid.addWidget(stop_button, 1, 4)

            if self.device_channel is None:  # For CC devices
                if self.device_name != "Sample Stage Rotator":
                    move_positive_button = QPushButton("Move +", self.choices_frame)
                    move_positive_button.setFont(button_font)
                    move_positive_button.setStyleSheet("background-color: Ivory;")
                    move_positive_button.clicked.connect(lambda: self.move_CCdevice(True))
                    choices_grid.addWidget(move_positive_button, 0, 4)

                    move_negative_button = QPushButton("Move -", self.choices_frame)
                    move_negative_button.setFont(button_font)
                    move_negative_button.setStyleSheet("background-color: Ivory;")
                    move_negative_button.clicked.connect(lambda: self.move_CCdevice(False))
                    choices_grid.addWidget(move_negative_button, 2, 4)

                if self.device_name == "Sample Stage Rotator":
                    rotate_positive_button = QPushButton("Rotate +", self.choices_frame)
                    rotate_positive_button.setFont(button_font)
                    rotate_positive_button.setStyleSheet("background-color: Ivory;")
                    rotate_positive_button.clicked.connect(lambda: self.move_CCdevice(True))
                    choices_grid.addWidget(rotate_positive_button, 0, 4)

                    rotate_negative_button = QPushButton("Rotate -", self.choices_frame)
                    rotate_negative_button.setFont(button_font)
                    rotate_negative_button.setStyleSheet("background-color: Ivory;")
                    rotate_negative_button.clicked.connect(lambda: self.move_CCdevice(False))
                    choices_grid.addWidget(rotate_negative_button, 2, 4)

            else:  # For KIM devices
                move_positive_button = QPushButton("Move +", self.choices_frame)
                move_positive_button.setFont(button_font)
                move_positive_button.setStyleSheet("background-color: Ivory;")
                move_positive_button.clicked.connect(lambda: self.move_KIMdevice(True))
                choices_grid.addWidget(move_positive_button, 0, 4)

                move_negative_button = QPushButton("Move -", self.choices_frame)
                move_negative_button.setFont(button_font)
                move_negative_button.setStyleSheet("background-color: Ivory;")
                move_negative_button.clicked.connect(lambda: self.move_KIMdevice(False))
                choices_grid.addWidget(move_negative_button, 2, 4)
            
            if self.device_channel is None:  # For CC devices
                apply_button = QPushButton("Apply Parameters", self.choices_frame)
                apply_button.setFont(button_font)
                apply_button.setStyleSheet("background-color: tan;")
                apply_button.clicked.connect(self.apply_parameters)
                choices_grid.addWidget(apply_button, 1, 9)
            else: # For KIM devices
                apply_bigbutton = QPushButton("Apply Coarse Parameters", self.choices_frame)
                apply_bigbutton.setFont(button_font)
                apply_bigbutton.setStyleSheet("background-color: tan;")
                apply_bigbutton.clicked.connect(self.apply_bigparameters)
                choices_grid.addWidget(apply_bigbutton, 2, 7)

                apply_smallbutton = QPushButton("Apply Fine Parameters", self.choices_frame)
                apply_smallbutton.setFont(button_font)
                apply_smallbutton.setStyleSheet("background-color: tan;")
                apply_smallbutton.clicked.connect(self.apply_smallparameters)
                choices_grid.addWidget(apply_smallbutton, 2, 12)


            self.choices_frame.setVisible(False)  # Hide the frame initially

    """------------------------------------------------------------------------------------------------------------------------------------------------------------"""

    # Implement open_camera, zooming, polygon manipulation methods for camera
    def open_camera(self):
        camera_thread = threading.Thread(target=camera_main)
        camera_thread.start()
        status_message = "Camera connected successfully."
        self.update_status(status_message)

    def capture(self):
        status_message = capture_frame(globals.Frame)
        self.update_status(status_message)

    # Function to handle Mode 1
    def trigger_mode1(self, event):
        status_message = "Continue tracking..."
        self.update_status(status_message)
        globals.mode = "tracking"

    # Function to handle Mode 2
    def trigger_mode2(self, event):
        status_message = "Start design a device..."
        self.update_status(status_message)
        globals.mode = "drawing"


    # Function to handle Mode 3
    def trigger_mode3(self, event):
        status_message = "Measuring..."
        self.update_status(status_message)
        globals.mode = "measuring"


    def zoom_in(self):
        zoom_in_camera()

    def zoom_out(self):
        zoom_out_camera()

    def fivefold(self):
        global parameters
        parameters["Camera"]["Rescale"] = (25580, 19060)
        status_message = "5X Microscope"
        self.update_status(status_message)
        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Conversion Size")
        success_dialog.setText(f"Conversion size: {parameters['Camera']['Rescale']}")
        success_dialog.exec_()

    def tenfold(self):
        global parameters
        parameters["Camera"]["Rescale"] = (25580 / 2, 19060 / 2)
        status_message = "10X Microscope"
        self.update_status(status_message)
        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Conversion Size")
        success_dialog.setText(f"Conversion size: {parameters['Camera']['Rescale']}")
        success_dialog.exec_()

    def twentyfold(self):
        global parameters
        parameters["Camera"]["Rescale"] = (25580 / 4, 19060 / 4)
        status_message = "20X Microscope"
        self.update_status(status_message)
        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Conversion Size")
        success_dialog.setText(f"Conversion size: {parameters['Camera']['Rescale']}")
        success_dialog.exec_()

    def retrieve_polygon(self):
        status_message = "Retrieving flake profile..."
        self.update_status(status_message)

        polygon_profile = get_polygon()  # Replace this with your actual code.
        formatted_profile = json.dumps(polygon_profile, indent=4, default=str)
        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Flake Profile")
        success_dialog.setText(f"Flake profile: \n{formatted_profile}")
        success_dialog.exec_()

        status_message = "Retrieved."
        self.update_status(status_message)

    def calibrate(self):
        global parameters

        status_message = "Calibrating flake..."
        self.update_status(status_message)

        # Calculate conversion factors
        device_steps_per_view_x = parameters["Camera"]["Rescale"][0]  # full device x movement
        device_steps_per_view_y = parameters["Camera"]["Rescale"][1]  # full device y movement
        camera_pixels_per_view_x = globals.original_frame_width  # full width of the camera image
        camera_pixels_per_view_y = globals.original_frame_height  # full height of the camera image
        camera_center = (globals.original_frame_width / 2, globals.original_frame_height / 2)

        conversion_factor_x = device_steps_per_view_x / camera_pixels_per_view_x
        conversion_factor_y = device_steps_per_view_y / camera_pixels_per_view_y

        polygon_profile = get_polygon()
        polygon_center = polygon_profile["center"]

        shift_vector = (camera_center[0] - polygon_center[0], camera_center[1] - polygon_center[1])

        success_dialog = QMessageBox()
        success_dialog.setWindowTitle("Calibration")
        success_dialog.setText(f"Shift_vector: {shift_vector}")
        success_dialog.exec_()

        # Convert shift vector to device steps
        shift_vector_device = (int(shift_vector[0] * conversion_factor_x), int(shift_vector[1] * conversion_factor_y))

        small_step_size_x = parameters["Sample Stage X-Axis"]["small_step_size"]
        small_step_size_y = parameters["Sample Stage Y-Axis"]["small_step_size"]

        step_x = int(shift_vector_device[0])
        velocity_x = parameters["Sample Stage X-Axis"]["CCvelocity"]
        if step_x >= 0:
            direction_x = False
        else:
            direction_x = True

        # Calculate the number of full small steps
        num_small_steps_x = step_x // small_step_size_x

        # Iterate over each small step
        for _ in range(num_small_steps_x):
            print(move_CCdevice(self.device_profile["servo"][1], "servo", None, direction_x, small_step_size_x,
                                velocity_x))

        # Handle any remainder after dividing by small_step_size
        remainder_x = int(step_x % small_step_size_x)
        if remainder_x > 0:
            print(move_CCdevice(self.device_profile["servo"][1], "servo", None, direction_x, remainder_x, velocity_x))

        step_y = -int(shift_vector_device[1])
        velocity_y = parameters["Sample Stage Y-Axis"]["CCvelocity"]
        if step_y >= 0:
            direction_y = False
        else:
            direction_y = True

        # Calculate the number of full small steps
        num_small_steps_y = step_y // small_step_size_y

        # Iterate over each small step
        for _ in range(num_small_steps_y):
            print(move_CCdevice(self.device_profile["servo"][2], "servo", None, direction_y, small_step_size_y,
                                velocity_y))

        # Handle any remainder after dividing by small_step_size
        remainder_y = int(step_y % small_step_size_y)
        if remainder_y > 0:
            print(move_CCdevice(self.device_profile["servo"][2], "servo", None, direction_y, remainder_y, velocity_y))

        status_message = "Calibrated."
        self.update_status(status_message)

    def align(self):
        global parameters

        if self.align_button.text() == "Align Flake":

            status_message = "Aligning flake..."
            self.update_status(status_message)

            shift_vector = get_shift()
            rotate_angle = get_angle()

            success_dialog = QMessageBox()
            success_dialog.setWindowTitle("Alignment")
            success_dialog.setText(f"Shift_vector: {shift_vector}, Rotate angle: {rotate_angle}")
            success_dialog.exec_()

            # Calculate conversion factors
            device_steps_per_view_x = parameters["Camera"]["Rescale"][0]  # full device x movement
            device_steps_per_view_y = parameters["Camera"]["Rescale"][1]  # full device y movement
            camera_pixels_per_view_x = 640  # full width of the camera image
            camera_pixels_per_view_y = 480  # full height of the camera image

            conversion_factor_x = device_steps_per_view_x / camera_pixels_per_view_x
            conversion_factor_y = device_steps_per_view_y / camera_pixels_per_view_y
            conversion_factor_rotate = 100000

            # Convert shift vector to device steps
            shift_vector_device = (
                int(shift_vector[0] * conversion_factor_x), int(shift_vector[1] * conversion_factor_y))
            rotate_vector_device = int(rotate_angle * conversion_factor_rotate)

            small_step_size_x = parameters["Sample Stage X-Axis"]["small_step_size"]
            small_step_size_y = parameters["Sample Stage Y-Axis"]["small_step_size"]
            small_angle_size = parameters["Sample Stage Rotator"]["small_angle_size"]

            step_x = int(shift_vector_device[0])
            velocity_x = 100
            if step_x >= 0:
                direction_x = False
            else:
                direction_x = True

            # # Calculate the number of full small steps
            # num_small_steps_x = step_x // small_step_size_x
            #
            # # Iterate over each small step
            # for _ in range(num_small_steps_x):
            #     print(move_CCdevice(self.device_profile["servo"][1], "servo", None, direction_x, small_step_size_x,
            #                         velocity_x))
            #
            # # Handle any remainder after dividing by small_step_size
            # remainder_x = int(step_x % small_step_size_x)
            # if remainder_x > 0:
            #     print(
            #         move_CCdevice(self.device_profile["servo"][1], "servo", None, direction_x, remainder_x, velocity_x))

            print(move_CCdevice(self.device_profile["servo"][1], "servo", None, direction_x, abs(step_x),
                                velocity_x))

            step_y = -int(shift_vector_device[1])
            velocity_y = 100
            if step_y >= 0:
                direction_y = False
            else:
                direction_y = True

            # Calculate the number of full small steps
            # num_small_steps_y = step_y // small_step_size_y
            #
            # # Iterate over each small step
            # for _ in range(num_small_steps_y):
            #     print(move_CCdevice(self.device_profile["servo"][2], "servo", None, direction_y, small_step_size_y,
            #                         velocity_y))
            #
            # # Handle any remainder after dividing by small_step_size
            # remainder_y = int(step_y % small_step_size_y)
            # if remainder_y > 0:
            #     print(
            #         move_CCdevice(self.device_profile["servo"][2], "servo", None, direction_y, remainder_y, velocity_y))

            print(move_CCdevice(self.device_profile["servo"][2], "servo", None, direction_y, abs(step_y),
                                velocity_y))

            velocity_r = 100
            if rotate_vector_device >= 0:
                direction_r = True
            else:
                direction_r = False

            # # Calculate the number of full small steps
            # num_small_steps_r = rotate_vector_device // small_angle_size
            #
            # # Iterate over each small step
            # for _ in range(num_small_steps_r):
            #     print(move_CCdevice(self.device_profile["servo"][3], "servo", None, direction_r, -small_angle_size,
            #                         velocity_r))
            #
            # # Handle any remainder after dividing by small_step_size
            # remainder_r = int(rotate_vector_device % small_angle_size)
            # if remainder_r > 0:
            #     print(move_CCdevice(self.device_profile["servo"][3], "servo", None, direction_r, -remainder_r,
            #                         velocity_r))

            print(move_CCdevice(self.device_profile["servo"][3], "servo", None, direction_r, -abs(rotate_vector_device),
                                velocity_r))
            status_message = "Aligned."
            self.update_status(status_message)

        elif self.align_button.text() == "Track Flake":
            pass

    def light_action(self, checked):
        if checked:
            # light is on, trigger action A
            globals.disaligning = False
            self.align_button.setText("Align Flake")
            status_message = "Start aligning..."
            self.update_status(status_message)
        else:
            # light is off, trigger action B
            globals.disaligning = True
            self.align_button.setText("Track Flake")
            status_message = "Continue tracking..."
            self.update_status(status_message)

    """------------------------------------------------------------------------------------------------------------------------------------------------------------"""

    # Implement connect_device, disconnect_device, stop_device, move_device, drive_device, update current position methods for Thorlab devices
    def connect_and_show_choices(self):
        self.connect_device()
        # Clear the stop event and start a new thread to update the position
        # self.stop_position_update_event.clear()
        # position_update_thread = threading.Thread(target=self.update_position_in_background)
        # position_update_thread.start()
        # self.update_position_label_from_queue()

    def show_hide_choices(self):
        if self.choices_frame.isVisible():
            self.choices_frame.setVisible(False)
            self.show_hide_button.setText("Choices")
        else:
            self.choices_frame.setVisible(True)
            self.show_hide_button.setText("Hide")

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
        step = int(self.step_entry.text())
        velocity = int(self.velocity_entry.text())
        status_message = move_CCdevice(self.device_serial_num, self.device_type, self.device_channel, direction, step,
                                       velocity)
        self.update_status(status_message)

    def move_KIMdevice(self, direction):
        global parameters
        step = int(self.step_entry.text())
        rate = int(self.rate_entry.text())
        acceleration = int(self.acceleration_entry.text())
        
        mode = int(parameters[self.device_name]["KIMjogmode"])
        status_message = move_KIMdevice(self.device_serial_num, self.device_type, self.device_channel, direction, step,
                                        rate, acceleration, mode)
        self.update_status(status_message)

    def drive_CCdevice(self, direction):
        # velocity =
        # Start driving the device in a new thread
        step = int(self.step_entry.text())
        velocity = int(self.velocity_entry.text())
        status_message = self.device_CCdriver.start_drive(self.device_serial_num, self.device_type, self.device_channel,
                                                          direction, step, velocity)
        self.update_status(status_message)

    def drive_KIMdevice(self, direction):
        # velocity =
        # Start driving the device in a new thread
        voltage = int(self.voltage_entry.text())
        rate = int(self.rate_entry.text())
        acceleration = int(self.acceleration_entry.text())
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
    
    def switch_jogmode(self):
        global parameters
        if self.mode == "Jog":
            self.mode = "Continuous"
            self.jogmode_button.setText("Continuous")
            parameters[self.device_name]["KIMjogmode"] = 1  # Function for Continuous mode
            status_message = "Continuous mode"
        else:
            self.mode = "Jog"
            self.jogmode_button.setText("Jog")
            parameters[self.device_name]["KIMjogmode"] = 2  # Function for Jog mode
            status_message = "Jog mode"
        self.update_status(status_message)
        

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
            try:
                parameters[self.device_name]["CCstep"] = float(self.step_entry.text())
                parameters[self.device_name]["CCvelocity"] = float(self.velocity_entry.text())
            except ValueError:
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Invalid input")
                error_dialog.setText("Please enter valid numbers.")
                error_dialog.exec_()
                return

            status_message = set_CCstep(self.device_serial_num, self.device_type, self.device_channel,
                                        parameters[self.device_name]["CCstep"])
            self.update_status(status_message)

            set_CCvelocity(self.device_serial_num, self.device_type, self.device_channel,
                           parameters[self.device_name]["CCvelocity"])

            if status_message == f"Device {self.device_serial_num.value.decode()} is not connected.":
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Parameters")
                error_dialog.setText(f"Parameters for {self.device_name} failed to be updated")
                error_dialog.exec_()
            else:
                success_dialog = QMessageBox()
                success_dialog.setWindowTitle("Parameters")
                success_dialog.setText(f"Parameters for {self.device_name} updated successfully")
                success_dialog.exec_()

    def apply_bigparameters(self):
        global parameters

        if self.device_channel is not None:
            try:
                parameters[self.device_name]["KIMstep"] = float(self.bigstep_entry.text())
                parameters[self.device_name]["KIMrate"] = float(self.bigrate_entry.text())
                parameters[self.device_name]["KIMacceleration"] = float(self.bigacceleration_entry.text())
                parameters[self.device_name]["KIMvoltage"] = float(self.bigvoltage_entry.text())
            except ValueError:
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Invalid input")
                error_dialog.setText("Please enter valid numbers.")
                error_dialog.exec_()
                return

            status_message = set_KIMjog(self.device_serial_num, self.device_type, self.device_channel,
                                        parameters[self.device_name]["KIMjogmode"],
                                        parameters[self.device_name]["KIMstep"],
                                        parameters[self.device_name]["KIMstep"],
                                        parameters[self.device_name]["KIMrate"],
                                        parameters[self.device_name]["KIMacceleration"])
            self.update_status(status_message)

            if status_message == f"Device {self.device_serial_num.value.decode()} Channel {self.device_channel} is not connected.":
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Parameters")
                error_dialog.setText(
                    f"Parameters for {self.device_name} Channel {self.device_channel} failed to be updated")
                error_dialog.exec_()
            else:
                success_dialog = QMessageBox()
                success_dialog.setWindowTitle("Parameters")
                success_dialog.setText(
                    f"Parameters for {self.device_name} Channel {self.device_channel} updated successfully")
                success_dialog.exec_()
    
    def apply_smallparameters(self):
        global parameters

        if self.device_channel is not None:
            try:
                parameters[self.device_name]["KIMstep"] = float(self.smallstep_entry.text())
                parameters[self.device_name]["KIMrate"] = float(self.smallrate_entry.text())
                parameters[self.device_name]["KIMacceleration"] = float(self.smallacceleration_entry.text())
                parameters[self.device_name]["KIMvoltage"] = float(self.smallvoltage_entry.text())
            except ValueError:
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Invalid input")
                error_dialog.setText("Please enter valid numbers.")
                error_dialog.exec_()
                return

            status_message = set_KIMjog(self.device_serial_num, self.device_type, self.device_channel,
                                        parameters[self.device_name]["KIMjogmode"],
                                        parameters[self.device_name]["KIMstep"],
                                        parameters[self.device_name]["KIMstep"],
                                        parameters[self.device_name]["KIMrate"],
                                        parameters[self.device_name]["KIMacceleration"])
            self.update_status(status_message)

            if status_message == f"Device {self.device_serial_num.value.decode()} Channel {self.device_channel} is not connected.":
                error_dialog = QMessageBox()
                error_dialog.setWindowTitle("Parameters")
                error_dialog.setText(
                    f"Parameters for {self.device_name} Channel {self.device_channel} failed to be updated")
                error_dialog.exec_()
            else:
                success_dialog = QMessageBox()
                success_dialog.setWindowTitle("Parameters")
                success_dialog.setText(
                    f"Parameters for {self.device_name} Channel {self.device_channel} updated successfully")
                success_dialog.exec_()

    def update_status(self, message):
        self.status_label.setText(message)