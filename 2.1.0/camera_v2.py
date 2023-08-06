import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
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


def mouse_callback(event, x, y, flags, param):
    
    global x_scale, y_scale, zoom_factor, top, left, frame
    global polygon, tracking, tracker, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, polygon_profile
    global drawing_polygon, drawing_polygons, drawing_dragging_index, drawing_closed, drawing_highlighted_point, drawing_dragging, drawing_poly_shifted, drawing_shift_vector, initial_center, color_index

    # Scaling for mouse coordinate
    x = int((x + left/2) / (x_scale * zoom_factor))
    y = int((y + top/2) / (y_scale * zoom_factor))

    # Drawing mode
    if globals.drawing_mode:
        handle_drawing_mode(event, x, y, flags, param)
    # Traking mode
    else:
        handle_tracking_mode(event, x, y, flags, param)

def handle_drawing_mode(event, x, y, flags, param):
    global drawing_polygon, drawing_polygons, drawing_dragging_index, drawing_closed, drawing_highlighted_point, drawing_dragging, drawing_poly_shifted, drawing_shift_vector, color_index

    if event == cv2.EVENT_LBUTTONDOWN:
        if drawing_closed and drawing_poly_shifted:
                drawing_dragging = False
                drawing_dragging_index = -1
                for draw_idx, (draw_polygon, _) in enumerate(drawing_polygons + [(drawing_polygon, None)]):
                    draw_poly_np = np.array(draw_polygon, dtype=np.int32)
                    if cv2.pointPolygonTest(draw_poly_np, (x, y), False) >= 0:
                        drawing_dragging = True
                        drawing_dragging_index = draw_idx
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
                drawing_polygons[drawing_dragging_index] = ([(draw_p[0] + draw_dx, draw_p[1] + draw_dy) for draw_p in draw_polygon], draw_color)

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

def handle_tracking_mode(event, x, y, flags, param):
    global polygon, tracking, tracker, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, polygon_profile

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


def capture_frame(frame):
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    filename = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
    if filename:
        cv2.imwrite(filename, frame)
        print(f"Captured frame saved to {filename}")
    else:
        print("Save operation cancelled")

def render_polygons_on_frame(frame):
    for draw_polygon, draw_color in drawing_polygons:
        cv2.polylines(frame, [np.array(draw_polygon, dtype=np.int32)], True, draw_color, 5)

    if drawing_closed:
        cv2.polylines(frame, [np.array(drawing_polygon, dtype=np.int32)], True, colors[color_index], 5)
    else:
        if drawing_polygon:
            for draw_point in drawing_polygon:
                if draw_point == drawing_highlighted_point:
                    cv2.circle(frame, draw_point, attraction_range, (0, 0, 255), 2)
            cv2.polylines(frame, [np.array(drawing_polygon, dtype=np.int32)], False, colors[color_index], 5)


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

            if not globals.drawing_mode:
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

            draw_frame(frame)

            # cv2.resizeWindow("Camera", 640, 480)
            cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)

            zoom_center = (frame.shape[1] / 2, frame.shape[0] / 2)
            M = cv2.getRotationMatrix2D(zoom_center, 0, zoom_factor)
            zoomed_frame = cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))
            # Resize window for display
            resized_frame = cv2.resize(zoomed_frame, (640, 480))

            cv2.imshow("Camera", resized_frame)

            globals.Frame = resized_frame

            # if polygon_profile['center']:  # If polygon_profile is not empty, print it out
            #     print(f"Center of polygon: {polygon_profile['center']}")
            #     print(f"Coordinates of polygon points: {polygon_profile['points']}")
            #     print(f"Edge lengths of polygon: {polygon_profile['edges']}")

            # polygon_profile = get_polygon()  # Replace this with your actual code.
            # print(f"Polygon profile: {polygon_profile}")
            if initial_center is not None:
                if polygon_profile['center']:  # Make sure the center is not None
                    center_shift_vector = (
                    polygon_profile['center'][0] - initial_center[0], polygon_profile['center'][1] - initial_center[1])

            if cv2.waitKey(20) & 0xFF == 27:
                break

        grabResult.Release()

    camera.StopGrabbing()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()