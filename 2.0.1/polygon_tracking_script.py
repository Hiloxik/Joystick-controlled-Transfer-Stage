import cv2
import numpy as np
import time

# Initialize variables

last_update_time = None
update_interval = 1.5  # Update every 1.5 seconds

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
frame = None
polygon_profile = {'center': None, 'points': [], 'edges': []}  # New variable
center_shift_vector = (0, 0)  # Initialize the shift vector to (0, 0)
previous_center = (0, 0)  # Initialize the previous center to (0, 0)

def draw_polygon(event, x, y, flags, param):
    global polygon, tracking, tracker, frame, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector, polygon_profile  # Added polygon_profile


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
        elif not polygon:
            polygon.append((x, y))
        else:
            for i, point in enumerate(polygon):
                dx, dy = point[0] - x, point[1] - y
                distance = np.sqrt(dx**2 + dy**2)
                if distance < attraction_range:
                    x, y = point
                    highlighted_point = point
                    if i == 0 and len(polygon) > 1:
                        closed = True
                        poly_shifted = polygon.copy()
                        bbox = cv2.boundingRect(np.array(poly_shifted, dtype=np.int32))
                        old_center = (bbox[0] + bbox[2]//2, bbox[1] + bbox[3]//2)
                        break
            if (x, y) not in polygon:
                polygon.append((x, y))
                closed = False
                highlighted_point = None

    elif event == cv2.EVENT_MOUSEMOVE:
        if dragging:
            dx, dy = x - shift_vector[0], y - shift_vector[1]
            shift_vector = (x, y)
            poly_shifted = [(p[0] + dx, p[1] + dy) for p in poly_shifted]
            bbox = cv2.boundingRect(np.array(poly_shifted, dtype=np.int32))
            old_center = (bbox[0] + bbox[2]//2, bbox[1] + bbox[3]//2)

            # Update the polygon_profile with the new coordinates and center
            center_x = sum(p[0] for p in poly_shifted) / len(poly_shifted)
            center_y = sum(p[1] for p in poly_shifted) / len(poly_shifted)
            polygon_profile['center'] = (center_x, center_y)
            polygon_profile['points'] = poly_shifted
            polygon_profile['edges'] = [np.sqrt((poly_shifted[i][0]-poly_shifted[i-1][0])**2 + (poly_shifted[i][1]-poly_shifted[i-1][1])**2) for i in range(1, len(poly_shifted))]
            polygon_profile['edges'].append(np.sqrt((poly_shifted[0][0]-poly_shifted[-1][0])**2 + (poly_shifted[0][1]-poly_shifted[-1][1])**2))  # Add the edge between the last and first points
        else:
            highlighted_point = None
            for point in polygon:
                dx, dy = point[0] - x, point[1] - y
                distance = np.sqrt(dx**2 + dy**2)
                if distance < attraction_range:
                    highlighted_point = point
                    break


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
            polygon_profile['edges'] = [np.sqrt((poly_shifted[i][0]-poly_shifted[i-1][0])**2 + (poly_shifted[i][1]-poly_shifted[i-1][1])**2) for i in range(1, len(poly_shifted))]
            polygon_profile['edges'].append(np.sqrt((poly_shifted[0][0]-poly_shifted[-1][0])**2 + (poly_shifted[0][1]-poly_shifted[-1][1])**2))  # Add the edge between the last and first points

def get_polygon():
    global polygon_profile
    return polygon_profile

def get_shift():
    global center_shift_vector
    return center_shift_vector

def draw_frame(frame):
    # Draw a sleek frame around the camera view
    thickness = 10  # Adjust the thickness to your preference
    color = (0, 0, 0)  # A light cyan color, but you can customize
    cv2.line(frame, (0, 0), (frame.shape[1], 0), color, thickness)
    cv2.line(frame, (0, 0), (0, frame.shape[0]), color, thickness)
    cv2.line(frame, (frame.shape[1]-1, 0), (frame.shape[1]-1, frame.shape[0]), color, thickness)
    cv2.line(frame, (0, frame.shape[0]-1), (frame.shape[1], frame.shape[0]-1), color, thickness)

def main():
    global polygon, tracking, tracker, frame, closed, highlighted_point, bbox, old_center, poly_shifted, dragging, shift_vector
    global bbox, polygon_profile, center_shift_vector, previous_center
    global last_update_time
    cv2.namedWindow("Camera")
    cv2.setMouseCallback("Camera", draw_polygon)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        exit()
    else:
        print("Camera connected successfully")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        if closed:
            if tracking:
                success, box = tracker.update(frame)
                if success:
                    new_center = (box[0] + box[2]//2, box[1] + box[3]//2)
                    dx, dy = new_center[0] - old_center[0], new_center[1] - old_center[1]
                    poly_shifted = [(x + dx, y + dy) for (x, y) in poly_shifted]
                    old_center = new_center

                    # Update the polygon_profile with the new coordinates and center
                    center_x = sum(p[0] for p in poly_shifted) / len(poly_shifted)
                    center_y = sum(p[1] for p in poly_shifted) / len(poly_shifted)
                    polygon_profile['center'] = (center_x, center_y)
                    polygon_profile['points'] = poly_shifted
                    polygon_profile['edges'] = [np.sqrt((poly_shifted[i][0]-poly_shifted[i-1][0])**2 + (poly_shifted[i][1]-poly_shifted[i-1][1])**2) for i in range(1, len(poly_shifted))]
                    polygon_profile['edges'].append(np.sqrt((poly_shifted[0][0]-poly_shifted[-1][0])**2 + (poly_shifted[0][1]-poly_shifted[-1][1])**2))  # Add the edge between the last and first points
                else:
                    cv2.putText(frame, "Tracking failure detected", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            cv2.polylines(frame, [np.array(poly_shifted, dtype=np.int32)], True, (0, 255, 0), 2)
        else:
            if polygon:
                for point in polygon:
                    if point == highlighted_point:
                        cv2.circle(frame, point, attraction_range, (0, 0, 255), 2)
                cv2.polylines(frame, [np.array(polygon, dtype=np.int32)], False, (0, 255, 0), 2)

        draw_frame(frame)
        cv2.imshow("Camera", frame)

        # if polygon_profile['center']:  # If polygon_profile is not empty, print it out
        #     print(f"Center of polygon: {polygon_profile['center']}")
        #     print(f"Coordinates of polygon points: {polygon_profile['points']}")
        #     print(f"Edge lengths of polygon: {polygon_profile['edges']}")

        # polygon_profile = get_polygon()  # Replace this with your actual code.
        # print(f"Polygon profile: {polygon_profile}")
        if polygon_profile['center']:  # Make sure the center is not None
            current_time = time.time()
            if last_update_time is None or current_time - last_update_time > update_interval:
                if (polygon_profile['center'][0] - previous_center[0], polygon_profile['center'][1] - previous_center[1]) != (0.0, 0.0):
                    center_shift_vector = (polygon_profile['center'][0] - previous_center[0], polygon_profile['center'][1] - previous_center[1])
                    previous_center = polygon_profile['center']
                else:
                    pass
                last_update_time = current_time
        
        # print(get_shift())

        if cv2.waitKey(20) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()