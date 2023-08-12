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


# Camera
original_frame_width, original_frame_height = None, None
disaligning = True
Frame = None
mode = "default"
radius = 0
center = None
origin_coordinate = None
uniformity = 0
flag = False