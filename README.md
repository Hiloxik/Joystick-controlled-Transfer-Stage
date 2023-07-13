# Joystick-controlled-Transfer-Stage
This repository contains python code to use a joystick and a GUI to control the transfer stage built by Thorlabs hardwares inside a traditional glove box.

The code mainly uses the package ctypes, which is a typical python package to exploit C++ commands. It is divided into several parts: connectivity.py to set the connection with the devices, movement.py to perform jogging, driving, stopping, etc. movements, position.py to report the real-time position of devices, newDeviceGUI.py to set up the joystick-device thread and the GUI-device thread, while main.py conclude all these programs and perform the final executation.

The hardwares are Thorlabs KDC motors and KIM piezo, which needs to be called by its original .dll files. The joystick is a Xbox 360 wirelss joystick.

This code can achieve using the remote joystick to control the transfer stage inside the glove box.


