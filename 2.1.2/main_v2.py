from GUI_v2 import * 
from camera_v2 import main as camera_main
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGroupBox, QTextEdit, QSplashScreen
from PyQt5.QtGui import QTextCursor, QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QThread
import sys
import datetime

# Output redirection class
class OutputRedirector:
    def __init__(self, console):
        self.console = console
        self.buffer = []
        self.last_update_time = datetime.datetime.now()


    def write(self, text):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.buffer.append(f"[{timestamp}] {text.rstrip()}")


        # Check if enough time has passed since the last update
        if (datetime.datetime.now() - self.last_update_time).seconds >= 0.01:
            self.flush()


    def flush(self):
        # Write all buffered lines to the console
        for line in self.buffer:
            self.console.append(line)
        self.console.moveCursor(QTextCursor.End)
        self.console.ensureCursorVisible()
        self.buffer = []
        self.last_update_time = datetime.datetime.now()


# get device serial numbers
device_profile = {
    "servo": [
        c_char_p(b"27256526"),
        c_char_p(b"27256127"),
        c_char_p(b"27256510"),
        c_char_p(b"55152924"),
    ],
    "inertial": [
        c_char_p(b"97100512"),
    ],
    "widget": [
        None,
    ]
}

joystick_state = {"Microscope": [False] * 13,
                  "Sample Stage X-Axis": [False] * 13,
                  "Sample Stage Y-Axis": [False] * 13,
                  "Sample Stage Rotator": [False] * 13,
                  "Stamp Stage X-Axis": [False] * 13,
                  "Stamp Stage Y-Axis": [False] * 13,
                  "Stamp Stage Z-Axis": [False] * 13,
                  "Last Moved Device": [False] * 13,
                  "Last Disconnected Device": [False] * 13}

# create a GUI window

app = QApplication([])

# Create a pixmap and draw text on it
# Create a QPixmap object from the image file path
pixmap = QPixmap(r"d:\大三下\科研\codes\joystick-transfer\ctypes\2.1.2\bg.jpg") # Update this with the actual path to your image file

# Scale the pixmap to the desired size
pixmap = pixmap.scaled(1500, 800, Qt.KeepAspectRatio)  # You can adjust the width and height as needed

# Create a QPainter object to draw on the QPixmap
painter = QPainter(pixmap)

# Set the font for the first text and draw it in the middle region
font = QFont('Gill Sans Bold', 40)
font.setBold(True)  # Make the font bold
painter.setFont(font)

# Set the pen color to white
painter.setPen(QColor(Qt.white))

# Calculate the x and y coordinates for the text to be centered, and convert them to integers
middle_x = int((pixmap.width() - painter.fontMetrics().width("TRANSFER STAGE REMOTE CONTROLLER")) / 2)
middle_y = int(pixmap.height() / 2)

# Draw the text using the integer coordinates
painter.drawText(middle_x, middle_y, "TRANSFER STAGE REMOTE CONTROLLER")

painter.setFont(QFont('Arial', 15))
dn_x = int((pixmap.width() - painter.fontMetrics().width("Initializing. . .")) / 2)
dn_y = int(pixmap.height() - 240)
painter.drawText(dn_x, dn_y, "Initializing. . .")


# Set the font for the second text and draw it in the down-right corner
painter.setFont(QFont('Arial', 15))
right_x = int(pixmap.width() - painter.fontMetrics().width("ver.1 Designed by Jiahui") - 60)
right_y = int(pixmap.height() - 20)
painter.drawText(right_x, right_y, "ver 2.1.2 Designed by Jiahui")

# Finish painting
painter.end()

# Create and show the splash screen as before
splash = QSplashScreen(pixmap)
splash.show()
app.processEvents()


# Create and show the splash screen
splash = QSplashScreen(pixmap)
splash.show()

# Ensures that the splash screen is displayed while the rest of the app initializes
app.processEvents()


window = QMainWindow()
window.setWindowTitle("Transfer Stage Remote Controller")
window.setGeometry(100, 100, 1000, 800)  # Specify the window size

# Create a frame inside main_window for each device GUI
central_widget = QWidget()
window.setCentralWidget(central_widget)
layout = QGridLayout()
central_widget.setLayout(layout)  # set layout to central_widget

# Create a QTextEdit for console output and add them to the layout
# console = QTextEdit()
# console.setReadOnly(True)
# layout.addWidget(console, 4, 0, 1, 2)  # Add it to the bottom row, first column

# sys.stdout = OutputRedirector(console)
# sys.stderr = OutputRedirector(console)

group_box_stylesheet = """
QGroupBox {
    font: 30px Cooper Black;/* Set the font size and style of the title */
    border: 2px solid gray; /* Set the width and color of the border */
    border-radius: 9px; /* Set the roundness of the corners */
    margin-top: 0.5em; /* Set the top margin */
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px; /* Set the left margin of the title */
    padding: 0 3px 0 3px; /* Set the padding around the title */
}
"""

# Create DeviceGUI instances and add them to the layout
microscope_gui = GUI("Microscope", device_profile["servo"][0], "servo", None, device_profile)
microscope_group = QGroupBox("Microscope")
microscope_group.setStyleSheet(group_box_stylesheet)
microscope_layout = QVBoxLayout()
microscope_layout.addWidget(microscope_gui)
microscope_group.setLayout(microscope_layout)
layout.addWidget(microscope_group, 0, 0)

sample_stage_x_gui = GUI("Sample Stage X-Axis", device_profile["servo"][1], "servo", None, device_profile)
sample_stage_x_group = QGroupBox("Sample Stage X-Axis")
sample_stage_x_group.setStyleSheet(group_box_stylesheet)
sample_stage_x_layout = QVBoxLayout()
sample_stage_x_layout.addWidget(sample_stage_x_gui)
sample_stage_x_group.setLayout(sample_stage_x_layout)
layout.addWidget(sample_stage_x_group, 1, 0)

sample_stage_y_gui = GUI("Sample Stage Y-Axis", device_profile["servo"][2], "servo", None, device_profile)
sample_stage_y_group = QGroupBox("Sample Stage Y-Axis")
sample_stage_y_group.setStyleSheet(group_box_stylesheet)
sample_stage_y_layout = QVBoxLayout()
sample_stage_y_layout.addWidget(sample_stage_y_gui)
sample_stage_y_group.setLayout(sample_stage_y_layout)
layout.addWidget(sample_stage_y_group, 2, 0)

sample_stage_rotator_gui = GUI("Sample Stage Rotator", device_profile["servo"][3], "servo", None, device_profile)
sample_stage_rotator_group = QGroupBox("Sample Stage Rotator")
sample_stage_rotator_group.setStyleSheet(group_box_stylesheet)
sample_stage_rotator_layout = QVBoxLayout()
sample_stage_rotator_layout.addWidget(sample_stage_rotator_gui)
sample_stage_rotator_group.setLayout(sample_stage_rotator_layout)
layout.addWidget(sample_stage_rotator_group, 3, 0)

stamp_stage_x_gui = GUI("Stamp Stage X-Axis", device_profile["inertial"][0], "inertial", 3, device_profile)
stamp_stage_x_group = QGroupBox("Stamp Stage X-Axis")
stamp_stage_x_group.setStyleSheet(group_box_stylesheet)
stamp_stage_x_layout = QVBoxLayout()
stamp_stage_x_layout.addWidget(stamp_stage_x_gui)
stamp_stage_x_group.setLayout(stamp_stage_x_layout)
layout.addWidget(stamp_stage_x_group, 0, 1)

stamp_stage_y_gui = GUI("Stamp Stage Y-Axis", device_profile["inertial"][0], "inertial", 2, device_profile)
stamp_stage_y_group = QGroupBox("Stamp Stage Y-Axis")
stamp_stage_y_group.setStyleSheet(group_box_stylesheet)
stamp_stage_y_layout = QVBoxLayout()
stamp_stage_y_layout.addWidget(stamp_stage_y_gui)
stamp_stage_y_group.setLayout(stamp_stage_y_layout)
layout.addWidget(stamp_stage_y_group, 1, 1)

stamp_stage_z_gui = GUI("Stamp Stage Z-Axis", device_profile["inertial"][0], "inertial", 1, device_profile)
stamp_stage_z_group = QGroupBox("Stamp Stage Z-Axis")
stamp_stage_z_group.setStyleSheet(group_box_stylesheet)
stamp_stage_z_layout = QVBoxLayout()
stamp_stage_z_layout.addWidget(stamp_stage_z_gui)
stamp_stage_z_group.setLayout(stamp_stage_z_layout)
layout.addWidget(stamp_stage_z_group, 2, 1)

widget_gui = GUI("Camera", device_profile["widget"][0], "widget", None, device_profile)
widget_group = QGroupBox("Camera")
widget_group.setStyleSheet(group_box_stylesheet)
widget_layout = QVBoxLayout()
widget_layout.addWidget(widget_gui)
widget_group.setLayout(widget_layout)
layout.addWidget(widget_group, 3, 1)

devices = [microscope_gui,
           sample_stage_x_gui,
           sample_stage_y_gui,
           sample_stage_rotator_gui,
           stamp_stage_x_gui,
           stamp_stage_y_gui,
           stamp_stage_z_gui]

device_name = ["Microscope",
               "Sample Stage X-Axis",
               "Sample Stage Y-Axis",
               "Sample Stage Rotator",
               "Stamp Stage X-Axis",
               "Stamp Stage Y-Axis",
               "Stamp Stage Z-Axis",
               "Last Moved Device",
               "Last Disconnected Device"]

# QThread.sleep(10)

# Close the splash screen and show the main window
splash.finish(window)
window.show()

camera_thread = threading.Thread(target=camera_main)
camera_thread.start()

# Initialize Joystick instance
joystick = Joystick(devices, device_name)

# Start the GUI event loop
controller = Controller(devices, joystick)
controller.start()

def on_closing():
    for device in devices:
        device.stop_device()
        device.disconnect_device()
    joystick.stop()

app.aboutToQuit.connect(on_closing)

app.exec_()