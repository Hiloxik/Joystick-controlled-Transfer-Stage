import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QFileDialog
# from pypylon import pylon
import sys
import globals

# Initial global variables

# Frame variables
original_frame_width, original_frame_height = None, None
x_scale, y_scale = 1, 1
zoom_factor = 1.0
top, left = 0, 0
frame_copy = None
frame = None

# Tracking mode variables
polygon = []
poly_shifted = []
closed = False
tracking = globals.tracking
highlighted_point = None
attraction_range = 10  # Attraction range around each point
old_center = None
bbox = None
tracker = None
dragging = False
shift_vector = (0, 0)
polygon_profile = {'center': None, 'points': [], 'edges': [], 'angle': 0}  # New variable

# Drawing mode variables
drawing_mode = False
drawing_polygon = []
drawing_polygons = []
drawing_dragging_index = -1
drawing_poly_shifted = []
drawing_closed = False
drawing_highlighted_point = None
drawing_dragging = False
drawing_shift_vector = (0, 0)
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
          (0, 255, 255)]  # Add more colors if needed
color_index = 0
center_shift_vector = (0, 0)  # Initialize the shift vector to (0, 0)
initial_center = None  # Store the initial center when the polygon is closed



def draw_polygon(event, x, y, flags, param):
    global x_scale, y_scale, zoom_factor, top, left, frame
    global polygon, tracking, tracker, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, polygon_profile
    global drawing_mode, drawing_polygon, drawing_polygons, drawing_dragging_index, drawing_closed, drawing_highlighted_point, \
        drawing_dragging, drawing_poly_shifted, drawing_shift_vector, initial_center, color_index
    
    x = int((x - left) / (x_scale * zoom_factor))
    y = int((y - top) / (y_scale * zoom_factor))

    if drawing_mode:
        if event == cv2.EVENT_LBUTTONDOWN:
            if drawing_closed and drawing_poly_shifted:
                drawing_dragging = False
                drawing_dragging_index = -1
                for idx, (polygon, _) in enumerate(drawing_polygons + [(drawing_polygon, None)]):
                    poly_np = np.array(polygon, dtype=np.int32)
                    if cv2.pointPolygonTest(poly_np, (x, y), False) >= 0:
                        drawing_dragging = True
                        drawing_dragging_index = idx
                        drawing_shift_vector = (x, y)
                        break
                else:
                    # If the mouse is clicked outside the polygon, start a new polygon
                    drawing_polygons.append(
                        (drawing_polygon.copy(), colors[color_index]))  # Save the current polygon with color
                    drawing_polygon = [(x, y)]  # Start new polygon
                    drawing_closed = False
                    drawing_highlighted_point = None
                    color_index = (color_index + 1) % len(colors)
            elif not drawing_polygon:
                drawing_polygon.append((x, y))
            else:
                for i, point in enumerate(drawing_polygon):
                    dx, dy = point[0] - x, point[1] - y
                    distance = np.sqrt(dx ** 2 + dy ** 2)
                    if distance < attraction_range:
                        x, y = point
                        drawing_highlighted_point = point
                        if i == 0 and len(drawing_polygon) > 1:
                            drawing_closed = True
                            drawing_poly_shifted = drawing_polygon.copy()

                            break
                if (x, y) not in drawing_polygon:
                    drawing_polygon.append((x, y))
                    drawing_closed = False
                    drawing_highlighted_point = None

        elif event == cv2.EVENT_MOUSEMOVE:
            if drawing_dragging:

                dx, dy = x - drawing_shift_vector[0], y - drawing_shift_vector[1]
                drawing_shift_vector = (x, y)
                if drawing_dragging_index == len(drawing_polygons):  # Current drawing_polygon
                    drawing_polygon = [(p[0] + dx, p[1] + dy) for p in drawing_polygon]
                else:  # Existing polygon in drawing_polygons
                    polygon, color = drawing_polygons[drawing_dragging_index]
                    drawing_polygons[drawing_dragging_index] = ([(p[0] + dx, p[1] + dy) for p in polygon], color)

            else:
                drawing_highlighted_point = None
                for point in drawing_polygon:
                    dx, dy = point[0] - x, point[1] - y
                    distance = np.sqrt(dx ** 2 + dy ** 2)
                    if distance < attraction_range:
                        drawing_highlighted_point = point
                        break

        elif event == cv2.EVENT_RBUTTONDOWN:
            if drawing_polygon:
                drawing_polygon = []
                drawing_poly_shifted = []
                drawing_closed = False
                drawing_highlighted_point = None
            elif drawing_polygons:
                drawing_polygons.pop()


        elif event == cv2.EVENT_LBUTTONUP:
            drawing_dragging = False

    else:

        if event == cv2.EVENT_LBUTTONDOWN:
            if closed and poly_shifted:
                poly_np = np.array(poly_shifted, dtype=np.int32)
                if cv2.pointPolygonTest(poly_np, (x, y), False) >= 0:
                    # If the mouse is clicked inside the polygon, start dragging the polygon
                    dragging = True
                    tracking = False
                    shift_vector = (x, y)
                else:
                    # If the mouse is clicked outside the polygon, start a new polygon
                    polygon = []
                    poly_shifted = []
                    closed = False
                    tracking = False
                    highlighted_point = None
                    polygon_profile['angle'] = 0

            elif not polygon:
                polygon.append((x, y))
            else:
                for i, point in enumerate(polygon):
                    dx, dy = point[0] - x, point[1] - y
                    distance = np.sqrt(dx ** 2 + dy ** 2)
                    if distance < attraction_range:
                        x, y = point
                        highlighted_point = point
                        if i == 0 and len(polygon) > 1:
                            closed = True
                            poly_shifted = polygon.copy()
                            bbox = cv2.boundingRect(np.array(poly_shifted, dtype=np.int32))
                            old_center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)
                            initial_center = (sum(p[0] for p in poly_shifted) / len(poly_shifted),
                                              sum(p[1] for p in poly_shifted) / len(poly_shifted))
                            polygon_profile['angle'] = 0

                            break
                if (x, y) not in polygon:
                    polygon.append((x, y))
                    closed = False
                    highlighted_point = None
                    polygon_profile['angle'] = 0

        elif event == cv2.EVENT_MOUSEMOVE:
            if dragging:
                dx, dy = x - shift_vector[0], y - shift_vector[1]
                shift_vector = (x, y)
                poly_shifted = [(p[0] + dx, p[1] + dy) for p in poly_shifted]
                bbox = cv2.boundingRect(np.array(poly_shifted, dtype=np.int32))
                old_center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)

                # Update the polygon_profile with the new coordinates and center
                center_x = sum(p[0] for p in poly_shifted) / len(poly_shifted)
                center_y = sum(p[1] for p in poly_shifted) / len(poly_shifted)
                polygon_profile['center'] = (center_x, center_y)
                polygon_profile['points'] = poly_shifted
                polygon_profile['edges'] = [np.sqrt(
                    (poly_shifted[i][0] - poly_shifted[i - 1][0]) ** 2 + (
                                poly_shifted[i][1] - poly_shifted[i - 1][1]) ** 2)
                    for i in range(1, len(poly_shifted))]
                polygon_profile['edges'].append(np.sqrt((poly_shifted[0][0] - poly_shifted[-1][0]) ** 2 + (
                        poly_shifted[0][1] - poly_shifted[-1][
                    1]) ** 2))  # Add the edge between the last and first points
            else:
                highlighted_point = None
                for point in polygon:
                    dx, dy = point[0] - x, point[1] - y
                    distance = np.sqrt(dx ** 2 + dy ** 2)
                    if distance < attraction_range:
                        highlighted_point = point
                        break

        elif event == cv2.EVENT_RBUTTONDOWN:
            polygon = []
            poly_shifted = []
            closed = False
            tracking = False
            highlighted_point = None
            polygon_profile['angle'] = 0

        elif event == cv2.EVENT_LBUTTONUP:
            dragging = False
            if closed:
                tracking = True
                tracker = cv2.legacy.TrackerMOSSE_create()
                tracker.init(frame, bbox)

                # Calculate the center and edge lengths of the polygon using poly_shifted
                center_x = sum(p[0] for p in poly_shifted) / len(poly_shifted)
                center_y = sum(p[1] for p in poly_shifted) / len(poly_shifted)
                polygon_profile['center'] = (center_x, center_y)
                polygon_profile['points'] = poly_shifted
                polygon_profile['edges'] = [np.sqrt(
                    (poly_shifted[i][0] - poly_shifted[i - 1][0]) ** 2 + (
                                poly_shifted[i][1] - poly_shifted[i - 1][1]) ** 2)
                    for i in range(1, len(poly_shifted))]
                polygon_profile['edges'].append(np.sqrt((poly_shifted[0][0] - poly_shifted[-1][0]) ** 2 + (
                        poly_shifted[0][1] - poly_shifted[-1][
                    1]) ** 2))  # Add the edge between the last and first points

        elif event == cv2.EVENT_MOUSEWHEEL:
            if closed:
                # Determine the direction of rotation
                rotation_angle = 1 if flags > 0 else -1
                # Calculate the center of the polygon
                center_x = sum(p[0] for p in poly_shifted) / len(poly_shifted)
                center_y = sum(p[1] for p in poly_shifted) / len(poly_shifted)
                center = (center_x, center_y)

                # Define the rotation matrix
                M = cv2.getRotationMatrix2D(center, rotation_angle, 1)

                # Rotate each point of the polygon
                poly_shifted_rotated = []
                for p in poly_shifted:
                    p_rotated = np.dot(M, (p[0], p[1], 1))
                    poly_shifted_rotated.append((p_rotated[0], p_rotated[1]))
                poly_shifted = poly_shifted_rotated

                # Recalculate the bounding box and center
                bbox = cv2.boundingRect(np.array(poly_shifted, dtype=np.int32))
                old_center = (bbox[0] + bbox[2] // 2, bbox[1] + bbox[3] // 2)

                # Update the polygon_profile with the new coordinates and center
                polygon_profile['center'] = center
                polygon_profile['points'] = poly_shifted
                polygon_profile['edges'] = [np.sqrt(
                    (poly_shifted[i][0] - poly_shifted[i - 1][0]) ** 2 + (
                                poly_shifted[i][1] - poly_shifted[i - 1][1]) ** 2)
                    for i in range(1, len(poly_shifted))]
                polygon_profile['edges'].append(np.sqrt((poly_shifted[0][0] - poly_shifted[-1][0]) ** 2 + (
                        poly_shifted[0][1] - poly_shifted[-1][
                    1]) ** 2))  # Add the edge between the last and first points
                polygon_profile['angle'] += rotation_angle


def turn_on_drawing_mode():
    global drawing_mode
    drawing_mode = True


def turn_off_drawing_mode():
    global drawing_mode
    drawing_mode = False


def get_polygon():
    global polygon_profile
    return polygon_profile


def get_shift():
    global center_shift_vector
    return center_shift_vector


def get_angle():
    return polygon_profile['angle']

def get_para():
    global original_frame_width, original_frame_height
    return original_frame_width, original_frame_height, tracking


def zoom_in_camera():
    global zoom_factor
    MAX_ZOOM = 5
    zoom_factor = min(zoom_factor + 0.1, MAX_ZOOM)


def zoom_out_camera():
    global zoom_factor
    MIN_ZOOM = 0.5
    zoom_factor = max(zoom_factor - 0.1, MIN_ZOOM)


def draw_frame(frame):
    # Draw a sleek frame around the camera view
    thickness = 10  # Adjust the thickness to your preference
    color = (0, 0, 0)  # A light cyan color, but you can customize
    cv2.line(frame, (0, 0), (frame.shape[1], 0), color, thickness)
    cv2.line(frame, (0, 0), (0, frame.shape[0]), color, thickness)
    cv2.line(frame, (frame.shape[1] - 1, 0), (frame.shape[1] - 1, frame.shape[0]), color, thickness)
    cv2.line(frame, (0, frame.shape[0] - 1), (frame.shape[1], frame.shape[0] - 1), color, thickness)


def capture_frame():
    global frame_copy
    app = QApplication(sys.argv) # You might already have this line elsewhere in your code
    options = QFileDialog.Options()
    file_name, _ = QFileDialog.getSaveFileName(None, "Save File", "", "PNG Files (*.png);;All Files (*)", options=options)
    if file_name:
        if not file_name.endswith('.png'):
            file_name += '.png'
        cv2.imwrite(file_name, frame_copy)
        print(f"Captured frame saved to {file_name}")
    else:
        print("Save operation cancelled")



def main():
    global original_frame_height, original_frame_width, x_scale, y_scale, zoom_factor, top, left, frame, frame_copy
    global polygon, tracking, tracker, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, bbox, polygon_profile, center_shift_vector
    global drawing_mode, drawing_polygon, drawing_polygons, drawing_closed, drawing_highlighted_point, \
        drawing_dragging, drawing_poly_shifted, drawing_shift_vector, initial_center, color_index

    # camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

    # # Grabbing Continuously (video) with minimal delay
    # camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    # converter = pylon.ImageFormatConverter()

    # # converting to opencv bgr format
    # converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    # converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    cv2.namedWindow("Camera")
    cv2.setMouseCallback("Camera", draw_polygon)

    # if camera.IsGrabbing():
    #     print("Camera connected successfully")

    # while camera.IsGrabbing():
    #     grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

    #     if grabResult.GrabSucceeded():
    #         # Access the image data
    #         image = converter.Convert(grabResult)
    #         frame = image.GetArray()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        exit()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break

        if original_frame_width is None or original_frame_height is None:
            original_frame_width, original_frame_height = frame.shape[1], frame.shape[0]
        

        zoomed_height = int(original_frame_height / zoom_factor)
        zoomed_width = int(original_frame_width / zoom_factor)

        # Determine the top-left corner of the zoomed region
        top = (original_frame_height - zoomed_height) // 2
        left = (original_frame_width - zoomed_width) // 2

        x_scale = 640 / original_frame_width
        y_scale = 480 / original_frame_height

        if drawing_mode:
            for polygon, color in drawing_polygons:
                cv2.polylines(frame, [np.array(polygon, dtype=np.int32)], True, color, 5)
            if drawing_closed:
                cv2.polylines(frame, [np.array(drawing_polygon, dtype=np.int32)], True, colors[color_index], 5)
            else:
                if drawing_polygon:
                    for point in drawing_polygon:
                        if point == drawing_highlighted_point:
                            cv2.circle(frame, point, attraction_range, (0, 0, 255), 2)
                    cv2.polylines(frame, [np.array(drawing_polygon, dtype=np.int32)], False, colors[color_index], 5)
        else:
            if closed:
                if tracking:
                    success, box = tracker.update(frame)
                    if success:
                        new_center = (box[0] + box[2] // 2, box[1] + box[3] // 2)
                        dx, dy = (new_center[0] - old_center[0]) / zoom_factor, (
                                new_center[1] - old_center[1]) / zoom_factor
                        poly_shifted = [(x + dx, y + dy) for (x, y) in poly_shifted]
                        old_center = new_center

                        # Update the polygon_profile with the new coordinates and center
                        center_x = sum(p[0] for p in poly_shifted) / len(poly_shifted)
                        center_y = sum(p[1] for p in poly_shifted) / len(poly_shifted)
                        polygon_profile['center'] = (center_x, center_y)
                        polygon_profile['points'] = poly_shifted
                        polygon_profile['edges'] = [np.sqrt((poly_shifted[i][0] - poly_shifted[i - 1][0]) ** 2 + (
                                poly_shifted[i][1] - poly_shifted[i - 1][1]) ** 2) for i in
                                                    range(1, len(poly_shifted))]
                        polygon_profile['edges'].append(np.sqrt((poly_shifted[0][0] - poly_shifted[-1][0]) ** 2 + (
                                poly_shifted[0][1] - poly_shifted[-1][
                            1]) ** 2))  # Add the edge between the last and first points
                    else:
                        cv2.putText(frame, "Tracking failure detected", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5,
                                    (0, 0, 255), 4)

                poly_shifted_zoomed = [(int(x * zoom_factor), int(y * zoom_factor)) for (x, y) in poly_shifted]
                cv2.polylines(frame, [np.array(poly_shifted_zoomed, dtype=np.int32)], True, (0, 255, 0), 5)
            else:
                if polygon:
                    for point in polygon:
                        if point == highlighted_point:
                            cv2.circle(frame, point, attraction_range, (0, 0, 255), 2)
                    cv2.polylines(frame, [np.array(polygon, dtype=np.int32)], False, (0, 255, 0), 5)
        
        for polygon, color in drawing_polygons:
                cv2.polylines(frame, [np.array(polygon, dtype=np.int32)], True, color, 5)
        if drawing_closed:
            cv2.polylines(frame, [np.array(drawing_polygon, dtype=np.int32)], True, colors[color_index], 5)
        else:
            if drawing_polygon:
                for point in drawing_polygon:
                    if point == drawing_highlighted_point:
                        cv2.circle(frame, point, attraction_range, (0, 0, 255), 2)
                cv2.polylines(frame, [np.array(drawing_polygon, dtype=np.int32)], False, colors[color_index], 5)

        draw_frame(frame)

        # cv2.resizeWindow("Camera", 640, 480)
        cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)

        zoom_center = (frame.shape[1] / 2, frame.shape[0] / 2)
        M = cv2.getRotationMatrix2D(zoom_center, 0, zoom_factor)
        zoomed_frame = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
        # Resize window for display
        resized_frame = cv2.resize(zoomed_frame, (640, 480))

        cv2.imshow("Camera", resized_frame)

        frame_copy = resized_frame.copy()

        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):  # Press 'c' to capture the frame
            capture_frame(frame)

        # if polygon_profile['center']:  # If polygon_profile is not empty, print it out
        #     print(f"Center of polygon: {polygon_profile['center']}")
        #     print(f"Coordinates of polygon points: {polygon_profile['points']}")
        #     print(f"Edge lengths of polygon: {polygon_profile['edges']}")

        # polygon_profile = get_polygon()  # Replace this with your actual code.
        # print(f"Polygon profile: {polygon_profile}")
        if polygon_profile['center']:  # Make sure the center is not None
            center_shift_vector = (
            polygon_profile['center'][0] - initial_center[0], polygon_profile['center'][1] - initial_center[1])

        if cv2.waitKey(20) & 0xFF == 27:
            break

    #     grabResult.Release()

    # camera.StopGrabbing()
    # cv2.destroyAllWindows()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()