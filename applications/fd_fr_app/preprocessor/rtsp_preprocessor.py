import cv2
import numpy as np
import urllib.request, json
import os

def resize_image(image):
    resized_image = cv2.resize(image, (1080, 720))
    return resized_image

def grayscale_conversion(image):
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray_img

def motion_detection(image_1, image_2):
    # Calculate absolute difference between the two frames
    frame_diff = cv2.absdiff(image_1, image_2)
    # Apply a threshold to extract significant differences
    _, thresholded_image = cv2.threshold(frame_diff, 30, 1, cv2.THRESH_BINARY)
    # Sum the values of thresholded_image, and obtain the ratio of 1s vs all pixels.
    sum_of_vals = np.sum(thresholded_image)
    count_of_vals = thresholded_image.size
    sum_to_count_ratio = sum_of_vals/count_of_vals
    # If it is greater than a hardcoded threshold, return a boolean value to main function
    if sum_to_count_ratio > 0.3:
        return True
    else:
        return False

if __name__ == "__main__":
    # Read from an RTSP stream
    # RTSP URL of the stream
    # rtsp_url = 'rtsp://localhost:8554/live'
    # Uncomment the following line before dockerizing
    rtsp_url = os.environ.get('RTSP_URL')

    # Open the RTSP stream
    cap = cv2.VideoCapture(rtsp_url)

    # Read the first frame from the stream
    while True:
        ret, prev_frame = cap.read()
        if prev_frame is not None:
            resized_image = resize_image(prev_frame)
            gray_image = grayscale_conversion(resized_image)
            break

    # Main loop for motion detection
    while True:
        # Read the frame from the stream
        ret, frame = cap.read()
        resized_image2 = resize_image(frame)
        gray_image2 = grayscale_conversion(resized_image2)

        # If motion_detection returns True, invoke face detection by passing image2
        if motion_detection(gray_image, gray_image2):
            # Call the FD microservice
            # base_url = 'http://127.0.0.1:4000'
            # Uncomment the following line before dockerizing
            base_url = os.environ.get('FD_URL')
            path = "/detect_face"
            url = base_url + path

            # Serialize the ndarray to JSON
            json_data = json.dumps(resized_image2.tolist())

            # Encode JSON data
            encoded_data = json_data.encode('utf-8')

            # Send POST request with JSON data
            req = urllib.request.Request(url, data=encoded_data, method='POST')
            req.add_header('Content-Type', 'application/json')

            response = urllib.request.urlopen(req)
            data = response.read()
            dict = json.loads(data)

            print(dict)

        # Update the previous frame
        gray_image = gray_image2