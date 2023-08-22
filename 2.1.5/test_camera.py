import cv2
import numpy as np

def calculate_color_uniformity(frame):
    # Convert the frame to grayscale if it is in color
    if len(frame.shape) == 3:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray_frame = frame

    # Compute the standard deviation of the grayscale values
    return np.std(gray_frame)

# Threshold for detecting a dramatic change in color uniformity
THRESHOLD = 50

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    exit()

if cap.isOpened():
    print("Camera connected successfully.")

last_uniformity = None
flag = False

while True:
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break
    
    # Calculate color uniformity
    uniformity = calculate_color_uniformity(frame)
    print(uniformity)
    
    if last_uniformity is not None:
        if abs(uniformity - last_uniformity) > THRESHOLD:
            print("Dramatic change in color uniformity detected.")
            flag = True
            break
    
    last_uniformity = uniformity

    # Optionally, display the frame
    cv2.imshow('frame', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Handle the flag if necessary
if flag:
    print("Handle the dramatic change in color uniformity here...")