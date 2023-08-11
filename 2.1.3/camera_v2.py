import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog
from pypylon import pylon
import globals

# Initialize variables

# Frame
x_scale, y_scale = 1, 1
zoom_factor = 1.0
top, left = 0, 0
frame = None

# Drawing mode
polygon = []
poly_shifted = []
closed = False
tracking = False
highlighted_point = None
attraction_range = 10  # Attraction range around each point
old_center = None
bbox = None
tracker = None
dragging = False
shift_vector = (0, 0)
polygon_profile = {'center': None, 'points': [], 'edges': [], 'angle': 0}  # New variable
center_shift_vector = (0, 0)  # Initialize the shift vector to (0, 0)
initial_center = None  # Store the initial center when the polygon is closed

# Tracking mode
drawing_polygon = []
drawing_polygons = []
drawing_dragging_index = -1
drawing_poly_shifted = []
drawing_closed = False
drawing_highlighted_point = None
drawing_dragging = False
drawing_shift_vector = (0, 0)
colors = [(255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
          (0, 255, 255), (255, 255, 255)]  # Add more colors if needed
color_index = 0

# Measuring mode
ruler_start = None
ruler_end = None


def mouse_callback(event, x, y, flags, param):
    global x_scale, y_scale, zoom_factor, top, left, frame
    global polygon, tracking, tracker, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, polygon_profile
    global drawing_polygon, drawing_polygons, drawing_dragging_index, drawing_closed, drawing_highlighted_point, \
        drawing_dragging, drawing_poly_shifted, drawing_shift_vector, initial_center, color_index
    global measuring_mode, ruler_start, ruler_end
    # Scaling for mouse coordinate
    x = int((x + left / 4) / (x_scale * zoom_factor))
    y = int((y + top / 4) / (y_scale * zoom_factor))

    # Measuring mode
    if globals.mode == "measuring":
        handle_measuring_mode(event, x, y, flags, param)
    # Drawing mode
    elif globals.mode == "drawing":
        handle_drawing_mode(event, x, y, flags, param)
    # Traking mode
    elif globals.mode == "tracking":
        handle_tracking_mode(event, x, y, flags, param)


def handle_drawing_mode(event, x, y, flags, param):
    global drawing_polygon, drawing_polygons, drawing_dragging_index, drawing_closed, drawing_highlighted_point, drawing_dragging, drawing_poly_shifted, drawing_shift_vector, color_index

    if event == cv2.EVENT_LBUTTONDOWN:
        if drawing_closed and drawing_poly_shifted:
            drawing_dragging = False
            drawing_dragging_index = -1
            if drawing_polygon:  # Only add if the polygon is not empty
                drawing_polygons.append((drawing_polygon, colors[color_index]))  # Add current polygon to list
            drawing_polygon = []  # Clear current polygon
            for draw_idx, (draw_polygon, _) in enumerate(drawing_polygons):
                if draw_polygon:  # Only test if the polygon is not empty
                    draw_poly_np = np.array(draw_polygon, dtype=np.int32)
                    if cv2.pointPolygonTest(draw_poly_np, (x, y), False) >= 0:
                        drawing_dragging = True
                        drawing_dragging_index = draw_idx
                        drawing_shift_vector = (x, y)
                        break
            else:
                # If the mouse is clicked outside the polygon, start a new polygon
                drawing_polygon = [(x, y)]  # Start new polygon
                drawing_closed = False
                drawing_highlighted_point = None
                color_index = (color_index + 1) % len(colors)


        elif not drawing_polygon:
            drawing_polygon.append((x, y))
        else:
            for draw_i, draw_point in enumerate(drawing_polygon):
                draw_dx, draw_dy = draw_point[0] - x, draw_point[1] - y
                draw_distance = np.sqrt(draw_dx ** 2 + draw_dy ** 2)
                if draw_distance < attraction_range:
                    x, y = draw_point
                    drawing_highlighted_point = draw_point
                    if draw_i == 0 and len(drawing_polygon) > 1:
                        drawing_closed = True
                        drawing_poly_shifted = drawing_polygon.copy()
                        break
            if (x, y) not in drawing_polygon:
                drawing_polygon.append((x, y))
                drawing_closed = False
                drawing_highlighted_point = None

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing_dragging:
            draw_dx, draw_dy = x - drawing_shift_vector[0], y - drawing_shift_vector[1]
            drawing_shift_vector = (x, y)
            if drawing_dragging_index == len(drawing_polygons):  # Current drawing_polygon
                drawing_polygon = [(draw_p[0] + draw_dx, draw_p[1] + draw_dy) for draw_p in drawing_polygon]
            else:  # Existing polygon in drawing_polygons
                draw_polygon, draw_color = drawing_polygons[drawing_dragging_index]
                drawing_polygons[drawing_dragging_index] = (
                    [(draw_p[0] + draw_dx, draw_p[1] + draw_dy) for draw_p in draw_polygon], draw_color)

        else:
            drawing_highlighted_point = None
            for draw_point in drawing_polygon:
                draw_dx, draw_dy = draw_point[0] - x, draw_point[1] - y
                draw_distance = np.sqrt(draw_dx ** 2 + draw_dy ** 2)
                if draw_distance < attraction_range:
                    drawing_highlighted_point = draw_point
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

    elif event == cv2.EVENT_MOUSEWHEEL:
        if drawing_closed:
            # Determine the direction of rotation
            draw_rotation_angle = 1 if flags > 0 else -1
            # Calculate the center of the polygon
            draw_center_x = sum(p[0] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
            draw_center_y = sum(p[1] for p in drawing_poly_shifted) / len(drawing_poly_shifted)
            draw_center = (draw_center_x, draw_center_y)

            # Define the rotation matrix
            draw_M = cv2.getRotationMatrix2D(draw_center, draw_rotation_angle, 1)

            # Rotate each point of the polygon
            drawing_poly_shifted_rotated = []
            for draw_p in drawing_poly_shifted:
                draw_p_rotated = np.dot(draw_M, (draw_p[0], draw_p[1], 1))
                drawing_poly_shifted_rotated.append((draw_p_rotated[0], draw_p_rotated[1]))
            drawing_poly_shifted = drawing_poly_shifted_rotated


def handle_tracking_mode(event, x, y, flags, param):
    global polygon, tracking, tracker, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, polygon_profile, initial_center

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
        if globals.disaligning:
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
        else:
            if closed:
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


def draw_ruler(image, start, end):
    if start is None or end is None:
        return

    # Draw the line
    cv2.line(image, start, end, (0, 255, 0), 2)

    # Draw caps "|"
    cap_length = 10
    cv2.line(image, (start[0], start[1] - cap_length), (start[0], start[1] + cap_length), (0, 255, 0), 2)
    cv2.line(image, (end[0], end[1] - cap_length), (end[0], end[1] + cap_length), (0, 255, 0), 2)

    # Calculate distance
    distance = int(np.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2))

    # Define the position for the text based on the direction of the line
    text_pos = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2 + 20)

    # Put text below the line
    cv2.putText(image, f"{distance} pixels", text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)


def handle_measuring_mode(event, x, y, flags, param):
    global ruler_start, ruler_end, frame

    # Scale the mouse coordinates based on your resizing
    x = int(x * frame.shape[1] / 640)
    y = int(y * frame.shape[0] / 480)

    if event == cv2.EVENT_LBUTTONDOWN:
        if ruler_start is None:
            ruler_start = (x, y)
        else:
            ruler_end = (x, y)
            distance = int(np.sqrt((ruler_end[0] - ruler_start[0]) ** 2 + (ruler_end[1] - ruler_start[1]) ** 2))
            # Reset ruler_start to allow drawing a new ruler
            ruler_start = None
            ruler_end = None

    elif event == cv2.EVENT_MOUSEMOVE and ruler_start is not None:
        # Draw temporary ruler on a copy of the frame
        draw_ruler(frame, ruler_start, (x, y))
        zoom_center = (frame.shape[1] / 2, frame.shape[0] / 2)
        M = cv2.getRotationMatrix2D(zoom_center, 0, zoom_factor)
        zoomed_frame = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
        resized_frame = cv2.resize(zoomed_frame, (640, 480))
        draw_scale_bar(resized_frame, zoom_factor)
        cv2.imshow("Camera", resized_frame)

    elif event == cv2.EVENT_RBUTTONDOWN:
        # Delete the ruler by resetting the frame
        ruler_start = None
        ruler_end = None
        zoom_center = (frame.shape[1] / 2, frame.shape[0] / 2)
        M = cv2.getRotationMatrix2D(zoom_center, 0, zoom_factor)
        zoomed_frame = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
        resized_frame = cv2.resize(zoomed_frame, (640, 480))

        cv2.imshow("Camera", resized_frame)


def get_polygon():
    global polygon_profile
    return polygon_profile


def get_shift():
    global center_shift_vector
    return center_shift_vector


def get_angle():
    return polygon_profile['angle']


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


class CaptureThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, frame, filename):
        super().__init__()
        self.frame = frame
        self.filename = filename

    def run(self):
        if not self.filename.endswith('.png'):
            self.filename += '.png'
        cv2.imwrite(self.filename, self.frame)
        self.finished.emit(f"Captured frame saved to {self.filename}")


def capture_frame(frame, parent_window=None):
    options = QFileDialog.Options()
    filename, _ = QFileDialog.getSaveFileName(parent_window, "Save File", "", "PNG files (*.png);;All files (*.*);;",
                                              options=options)

    if filename:
        capture_thread = CaptureThread(frame, filename)
        capture_thread.finished.connect(lambda message: print(message))
        capture_thread.start()
        return capture_thread
    else:
        return "Save operation cancelled"


def render_polygons_on_frame(frame):
    for draw_polygon, draw_color in drawing_polygons:
        cv2.polylines(frame, [np.array(draw_polygon, dtype=np.int32)], True, draw_color, 5)

    if drawing_closed:
        cv2.polylines(frame, [np.array(drawing_poly_shifted, dtype=np.int32)], True, colors[color_index], 5)
    else:
        if drawing_polygon:
            for draw_point in drawing_polygon:
                if draw_point == drawing_highlighted_point:
                    cv2.circle(frame, draw_point, attraction_range, (0, 0, 255), 2)
            cv2.polylines(frame, [np.array(drawing_polygon, dtype=np.int32)], False, colors[color_index], 5)


def draw_scale_bar(frame, zoom_factor):
    # Determine the length of the horizontal part of the scale bar in pixels, based on the zoom factor
    scale_bar_length = 100 / zoom_factor

    # Determine the start and end points for the horizontal part of the scale bar
    start_point_horizontal = (20, frame.shape[0] - 20)  # 20 pixels from the left-bottom corner
    end_point_horizontal = (int(start_point_horizontal[0] + scale_bar_length), start_point_horizontal[1])

    # Determine the start and end points for the vertical parts of the scale bar
    start_point_vertical_left = (start_point_horizontal[0], start_point_horizontal[1] - 5)
    end_point_vertical_left = (start_point_horizontal[0], start_point_horizontal[1] + 5)

    start_point_vertical_right = (end_point_horizontal[0], end_point_horizontal[1] - 5)
    end_point_vertical_right = (end_point_horizontal[0], end_point_horizontal[1] + 5)

    # Draw the horizontal line representing the main part of the scale bar
    cv2.line(frame, start_point_horizontal, end_point_horizontal, (0, 0, 0), 2)

    # Draw the vertical lines at both ends of the scale bar
    cv2.line(frame, start_point_vertical_left, end_point_vertical_left, (0, 0, 0), 2)
    cv2.line(frame, start_point_vertical_right, end_point_vertical_right, (0, 0, 0), 2)

    # Add text next to the scale bar indicating its real-world length
    text = f"{100} units"  # Change this according to the real-world length represented by the scale bar
    cv2.putText(frame, text, (end_point_horizontal[0] + 5, end_point_horizontal[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 0, 0), 2)


def main():
    global x_scale, y_scale, zoom_factor, top, left, frame
    global polygon, tracking, tracker, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, bbox, polygon_profile, center_shift_vector
    global drawing_polygon, drawing_polygons, drawing_closed, drawing_highlighted_point, \
        drawing_dragging, drawing_poly_shifted, drawing_shift_vector, initial_center, color_index

    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

    # Grabbing Continuously (video) with minimal delay
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    converter = pylon.ImageFormatConverter()

    # converting to opencv bgr format
    converter.OutputPixelFormat = pylon.PixelType_BGR8packed
    converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

    cv2.namedWindow("Camera")
    cv2.setMouseCallback("Camera", mouse_callback)

    if camera.IsGrabbing():
        print("Camera connected successfully")

    while camera.IsGrabbing():
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            # Access the image data
            image = converter.Convert(grabResult)
            frame = image.GetArray()

    # cap = cv2.VideoCapture(0)
    # if not cap.isOpened():
    #     print("Cannot open camera")
    #     exit()
    #
    # if cap.isOpened():
    #     print("Camera connected successfully.")
    #
    # while True:
    #     ret, frame = cap.read()
    #     if not ret:
    #         print("Can't receive frame (stream end?). Exiting ...")
    #         break
            if globals.original_frame_width is None or globals.original_frame_height is None:
                globals.original_frame_width, globals.original_frame_height = frame.shape[1], frame.shape[0]

            zoomed_height = int(globals.original_frame_height / zoom_factor)
            zoomed_width = int(globals.original_frame_width / zoom_factor)

            # Determine the top-left corner of the zoomed region
            top = (globals.original_frame_height - zoomed_height)
            left = (globals.original_frame_width - zoomed_width)

            x_scale = 640 / globals.original_frame_width
            y_scale = 480 / globals.original_frame_height

            render_polygons_on_frame(frame)

            if globals.mode == "measuring":
                if ruler_start and ruler_end:
                    cv2.line(frame, ruler_start, ruler_end, (0, 0, 255), 2)

            elif globals.mode == "tracking":
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

                    # poly_shifted_zoomed = [(int(x * zoom_factor), int(y * zoom_factor)) for (x, y) in poly_shifted]
                    cv2.polylines(frame, [np.array(poly_shifted, dtype=np.int32)], True, (0, 255, 0), 5)
                else:
                    if polygon:
                        for point in polygon:
                            if point == highlighted_point:
                                cv2.circle(frame, point, attraction_range, (0, 0, 255), 2)
                        cv2.polylines(frame, [np.array(polygon, dtype=np.int32)], False, (0, 255, 0), 5)

            draw_frame(frame)

            # cv2.resizeWindow("Camera", 640, 480)
            cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)

            zoom_center = (frame.shape[1] / 2, frame.shape[0] / 2)
            M = cv2.getRotationMatrix2D(zoom_center, 0, zoom_factor)
            zoomed_frame = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
            # Resize window for display
            resized_frame = cv2.resize(zoomed_frame, (640, 480))

            draw_scale_bar(resized_frame, zoom_factor)

            cv2.imshow("Camera", resized_frame)

            globals.Frame = resized_frame

            # if polygon_profile['center']:  # If polygon_profile is not empty, print it out
            #     print(f"Center of polygon: {polygon_profile['center']}")
            #     print(f"Coordinates of polygon points: {polygon_profile['points']}")
            #     print(f"Edge lengths of polygon: {polygon_profile['edges']}")

            # polygon_profile = get_polygon()  # Replace this with your actual code.
            # print(f"Polygon profile: {polygon_profile}")

            # print(polygon_profile['center'])
            if polygon_profile['center']:  # Make sure the center is not None
                center_shift_vector = (
                    polygon_profile['center'][0] - initial_center[0], polygon_profile['center'][1] - initial_center[1])

            if cv2.waitKey(20) & 0xFF == 27:
                break

        grabResult.Release()

    camera.StopGrabbing()
    cv2.destroyAllWindows()
    # cap.release()
    # cv2.destroyAllWindows()


if __name__ == "__main__":
    main()