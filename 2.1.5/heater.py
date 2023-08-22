import win32com.client
import time

labview = win32com.client.Dispatch("Labview.Application")

vi_path = r"C:\Users\Wang_glove box\Desktop\PID\PID Ramp 5_v19\PID Ramp 5.vi"  # Replace with your VI path
vi = labview.getvireference(vi_path)
if vi is None:
    print("Failed to obtain VI reference")
else:
    # Open the front panel
    vi.FPWinOpen = True


    input("Press Enter after you have manually started the VI...")

    new_value = 0
    while True:
        # Set the control value
        control_name = "SP:"
        new_value += 1
        vi.SetControlValue(control_name, new_value)
        print(f"Set {control_name} to {new_value}")
        time.sleep(1)