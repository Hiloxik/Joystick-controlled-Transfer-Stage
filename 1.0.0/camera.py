"""This code is for the final connection with the Basler camera in glove box."""

import cv2
import numpy as np
from pypylon import pylon
from sklearn.cluster import KMeans


def GausBlur(img):
    gaus = cv2.GaussianBlur(img, (11, 11), 2)
    return gaus


def create_hsv_mask(image, lower, upper):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    result = cv2.bitwise_and(image, image, mask=mask)
    return result


def Gray_img(mask_img):
    gray = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
    return gray


def open_mor(binary):
    kernel = np.ones((6, 6), np.uint8)
    opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=5)
    return opening


# connecting to the first available camera
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

# Grabbing Continuously (video) with minimal delay
camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
converter = pylon.ImageFormatConverter()

# converting to opencv bgr format
converter.OutputPixelFormat = pylon.PixelType_BGR8packed
converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

frame_count = 0
process_every_nth_frame = 1  # Process every 5 frames

while camera.IsGrabbing():
    grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

    if grabResult.GrabSucceeded():
        # Access the image data
        image = converter.Convert(grabResult)
        img = image.GetArray()

        frame_count += 1
        if frame_count % process_every_nth_frame == 0:  # Process every nth frame

            img = cv2.resize(img, (640, 480))  # Reduced resolution

            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            pixels = hsv.reshape((-1, 3))

            # Perform the clustering and fit to the pixel data
            tolerance = 4000000  # Adjust as needed
            residue = np.inf
            d = 2

            while residue > tolerance:
                # Perform the clustering and fit to the pixel data
                kmeans = KMeans(n_clusters=d)
                kmeans.fit(pixels)

                # Replace each pixel value with its corresponding centroid value
                clustered_pixels = kmeans.cluster_centers_[kmeans.labels_]

                # Compute the residue
                residue = np.sum(np.abs(pixels - clustered_pixels))

                print(f'Residue with {d} clusters: {residue}')
                d += 1

            lower_ranges = []
            upper_ranges = []

            for i in range(len(kmeans.cluster_centers_)):
                lower_ranges.append(np.min(kmeans.cluster_centers_[i], axis=0))
                upper_ranges.append(np.max(kmeans.cluster_centers_[i], axis=0))

            gaus_img = GausBlur(img)
            for i in range(kmeans.n_clusters):
                lower = np.array([lower_ranges[i], 100, 100])
                upper = np.array([upper_ranges[i], 255, 255])
                mask_img = create_hsv_mask(gaus_img, lower, upper)
                gray_img = Gray_img(mask_img)
                ret, binary = cv2.threshold(gray_img, 1, 255, cv2.THRESH_BINARY)
                open_img = open_mor(binary)
                contours, hierarchy = cv2.findContours(open_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                min_contour_area = 2000
                max_contour_area = 50000
                contours = [c for c in contours if min_contour_area < cv2.contourArea(c) < max_contour_area]
                print('Number of objects detected:', len(contours))
                for i, c in enumerate(sorted(contours, key=cv2.contourArea, reverse=True)):
                    rect = cv2.minAreaRect(c)
                    box = np.int0(cv2.boxPoints(rect))
                    cv2.drawContours(img, [box], -1, (0, 255, 0), 3)
                    # cv2.putText(img, 'object' + str(i + 1), (box[0][0], box[0][1]), cv2.FONT_HERSHEY_SIMPLEX, 2,
                    #             (0, 0, 255), 1)
                # img = cv2.resize(img, (640,480))
            cv2.imshow("Image", img)  # Display the processed image

        else:  # If not nth frame, just show the unprocessed image in the same window
            img = cv2.resize(img, (640, 480))
            cv2.imshow("Image", img)  # Display the raw image

        k = cv2.waitKey(1)
        if k == 27:
            break
    grabResult.Release()

# Releasing the camera
camera.StopGrabbing()
cv2.destroyAllWindows()