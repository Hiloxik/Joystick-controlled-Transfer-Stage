from newDeviceGUI import *  # Import your new GUI class

# get device serial numbers
device_serial_numbers = [serial_num1,
                         serial_num2,
                         serial_num3,
                         serial_num4,
                         serial_num5,
                         serial_num6,
                         serial_num7,
                         serial_num8]

# Global joystick state dictionary
joystick_state = {"Microscope": [False] * 7,
                  "Sample Stage X-Axis": [False] * 7,
                  "Sample Stage Y-Axis": [False] * 7,
                  "Sample Stage Rotator": [False] * 7,
                  "Microscope Rotor": [False] * 7,
                  "Stamp Stage X-Axis": [False] * 7,
                  "Stamp Stage Y-Axis": [False] * 7,
                  "Stamp Stage Z-Axis": [False] * 7}

# create a GUI window
main_window = ThemedTk(theme="aqua")  # use the "aqua" theme, for instance
main_window.title("Motor Controller Main GUI")
main_window.geometry('1000x800')  # Specify the window size

# Create a frame inside main_window for each device GUI
microscope_frame = tk.Frame(main_window)
microscope_frame.grid(row=0, column=0)
sample_stage_x_frame = tk.Frame(main_window)
sample_stage_x_frame.grid(row=1, column=0)
sample_stage_y_frame = tk.Frame(main_window)
sample_stage_y_frame.grid(row=2, column=0)
sample_stage_rotator_frame = tk.Frame(main_window)
sample_stage_rotator_frame.grid(row=3, column=0)
joystick_frame = tk.Frame(main_window)
joystick_frame.grid(row=4, column=0)

microscope_rotor_frame = tk.Frame(main_window)
microscope_rotor_frame.grid(row=0, column=1)
stamp_stage_x_frame = tk.Frame(main_window)
stamp_stage_x_frame.grid(row=1, column=1)
stamp_stage_y_frame = tk.Frame(main_window)
stamp_stage_y_frame.grid(row=2, column=1)
stamp_stage_z_frame = tk.Frame(main_window)
stamp_stage_z_frame.grid(row=3, column=1)

# Create DeviceGUI instances inside their frames
microscope_gui = GUI(microscope_frame, "Microscope", serial_num1)
sample_stage_x_gui = GUI(sample_stage_x_frame, "Sample Stage X-Axis", serial_num2)
sample_stage_y_gui = GUI(sample_stage_y_frame, "Sample Stage Y-Axis", serial_num3)
sample_stage_rotator_gui = GUI(sample_stage_rotator_frame, "Sample Stage Rotator", serial_num4)
microscope_rotor_gui = GUI(microscope_rotor_frame, "Microscope Rotor", serial_num5)
stamp_stage_x_gui = GUI(stamp_stage_x_frame, "Stamp Stage X-Axis", serial_num6)
stamp_stage_y_gui = GUI(stamp_stage_y_frame, "Stamp Stage Y-Axis", serial_num7)
stamp_stage_z_gui = GUI(stamp_stage_z_frame, "Stamp Stage Z-Axis", serial_num8)

devices = [microscope_gui,
           sample_stage_x_gui,
           sample_stage_y_gui,
           sample_stage_rotator_gui,
           microscope_rotor_gui,
           stamp_stage_x_gui,
           stamp_stage_y_gui,
           stamp_stage_z_gui]

device_name = ["Microscope",
               "Sample Stage X-Axis",
               "Sample Stage Y-Axis",
               "Sample Stage Rotator",
               "Microscope Rotor",
               "Stamp Stage X-Axis",
               "Stamp Stage Y-Axis",
               "Stamp Stage Z-Axis"]

# Initialize Joystick instance
joystick = Joystick(devices, device_name)


# Start the GUI event loop
controller = Controller(devices, joystick)
controller.start()

def on_closing():
    for device in devices:
        device.stop_device()
        device.disconnect_device()
    joystick.stop()  # stop the joystick_loop
    main_window.destroy()
    main_window.quit()


main_window.protocol("WM_DELETE_WINDOW", on_closing)

main_window.mainloop()