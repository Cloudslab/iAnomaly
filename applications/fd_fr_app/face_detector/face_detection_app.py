# Read from the request content and also set the base_url to read from configmap.

import json
from flask import Flask, request, jsonify
from src.get_nets import PNet, RNet, ONet
import cv2
import numpy as np
from collections import OrderedDict
import time
from src.first_stage import run_first_stage_parallel_half
from src.box_utils import nms, calibrate_box, get_image_boxes, convert_to_square
import torch
from torch.autograd import Variable
from src.matlab_cp2tform import get_similarity_transform_for_cv2
import urllib.request
import os

app = Flask(__name__)

# Function to load the model
def loadFDModel(device):
    # The FD model consists of 3 models; pnet, rnet and onet
    pnet = PNet().to(device)
    rnet = RNet().to(device)
    onet = ONet().to(device)
    pnet.eval()
    rnet.eval()
    onet.eval()
    return pnet, rnet, onet

def detect_faces(image, pnet, rnet, onet, min_face_size=20.0,
                 thresholds=[0.6, 0.7, 0.8],
                 nms_thresholds=[0.7, 0.7, 0.7], device='cpu'):
    """
    Arguments:
        image: an instance of PIL.Image.
        min_face_size: a float number.
        pnet: Proposal network
        rnet: Refinement network
        onet: output network
        thresholds: a list of length 3.
        nms_thresholds: a list of length 3.

    Returns:
        two float numpy arrays of shapes [n_boxes, 4] and [n_boxes, 10],
        bounding boxes and facial landmarks.
    """

    # BUILD AN IMAGE PYRAMID
    # width, height = image.size
    height, width, _ = image.shape
    min_length = min(height, width)

    min_detection_size = 12
    factor = 0.5

    # scales for scaling the image
    scales = []

    # scales the image so that
    # minimum size that we can detect equals to
    # minimum face size that we want to detect
    m = min_detection_size / min_face_size
    min_length *= m

    factor_count = 0
    while min_length > min_detection_size:
        scales.append(m * factor ** factor_count)
        min_length *= factor
        factor_count += 1
    # STAGE 1

    # it will be returned
    bounding_boxes = []

    # run P-Net on different scales
    t = time.time()
    if factor == 0.5:
        bounding_boxes = run_first_stage_parallel_half(image, pnet, scale_list=scales, threshold=thresholds[0],
                                                       device=device)
    if DEBUG:
        print("first stage", time.time() - t)
    t = time.time()
    # collect boxes (and offsets, and scores) from different scales
    # bounding_boxes = [i for i in bounding_boxes if i is not None]
    if len(bounding_boxes) == 0:
        return [], []
    bounding_boxes = np.vstack(bounding_boxes)

    keep = nms(bounding_boxes[:, 0:5], nms_thresholds[0])
    if DEBUG:
        print("nms", time.time() - t)
    t = time.time()
    bounding_boxes = bounding_boxes[keep]

    # use offsets predicted by pnet to transform bounding boxes
    bounding_boxes = calibrate_box(bounding_boxes[:, 0:5], bounding_boxes[:, 5:])
    if DEBUG:
        print("calibrate", time.time() - t)
    t = time.time()
    # shape [n_boxes, 5]

    bounding_boxes = convert_to_square(bounding_boxes)
    bounding_boxes[:, 0:4] = np.round(bounding_boxes[:, 0:4])
    if DEBUG:
        print("convert to sq", time.time() - t)
    t = time.time()
    # STAGE 2

    img_boxes = get_image_boxes(bounding_boxes, image, size=24)
    if DEBUG:
        print("get img boxes", time.time() - t)
    t = time.time()
    if len(img_boxes) == 0:
        return [], []
    with torch.no_grad():
        img_boxes = Variable(torch.FloatTensor(img_boxes).to(device))
        output = rnet(img_boxes)
    offsets = output[0].cpu().data.numpy()  # shape [n_boxes, 4]
    probs = output[1].cpu().data.numpy()  # shape [n_boxes, 2]
    if DEBUG:
        print("second stage", time.time() - t)
    t = time.time()
    keep = np.where(probs[:, 1] > thresholds[1])[0]
    bounding_boxes = bounding_boxes[keep]
    bounding_boxes[:, 4] = probs[keep, 1].reshape((-1,))
    offsets = offsets[keep]

    keep = nms(bounding_boxes, nms_thresholds[1])
    if DEBUG:
        print("nms", time.time() - t)
    t = time.time()
    bounding_boxes = bounding_boxes[keep]
    bounding_boxes = calibrate_box(bounding_boxes, offsets[keep])
    bounding_boxes = convert_to_square(bounding_boxes)
    bounding_boxes[:, 0:4] = np.round(bounding_boxes[:, 0:4])
    if DEBUG:
        print("calibrate+square", time.time() - t)
    t = time.time()
    # STAGE 3

    img_boxes = get_image_boxes(bounding_boxes, image, size=48)
    if DEBUG:
        print("img boxes", time.time() - t)
    t = time.time()
    if len(img_boxes) == 0:
        return [], []
    with torch.no_grad():
        img_boxes = Variable(torch.FloatTensor(img_boxes).to(device))
        output = onet(img_boxes)
    landmarks = output[0].cpu().data.numpy()  # shape [n_boxes, 10]
    offsets = output[1].cpu().data.numpy()  # shape [n_boxes, 4]
    probs = output[2].cpu().data.numpy()  # shape [n_boxes, 2]
    if DEBUG:
        print("stage 3", time.time() - t)
    t = time.time()
    keep = np.where(probs[:, 1] > thresholds[2])[0]
    bounding_boxes = bounding_boxes[keep]
    bounding_boxes[:, 4] = probs[keep, 1].reshape((-1,))
    offsets = offsets[keep]
    landmarks = landmarks[keep]

    # compute landmark points
    width = bounding_boxes[:, 2] - bounding_boxes[:, 0] + 1.0
    height = bounding_boxes[:, 3] - bounding_boxes[:, 1] + 1.0
    xmin, ymin = bounding_boxes[:, 0], bounding_boxes[:, 1]
    landmarks[:, 0:5] = np.expand_dims(xmin, 1) + np.expand_dims(width, 1) * landmarks[:, 0:5]
    landmarks[:, 5:10] = np.expand_dims(ymin, 1) + np.expand_dims(height, 1) * landmarks[:, 5:10]

    bounding_boxes = calibrate_box(bounding_boxes, offsets)
    keep = nms(bounding_boxes, nms_thresholds[2], mode='min')
    bounding_boxes = bounding_boxes[keep]
    landmarks = landmarks[keep]
    if DEBUG:
        print("nms+op", time.time() - t)
    t = time.time()
    return bounding_boxes, landmarks

def DetectLandmarks(img, net_list, min_face_size=60.0, device='cpu'):
    """
    Given an image detects faces in the image and returns corresponding facial landmarks and bounding boxes
    :param img: cv2 instance
    :return: dictionary of landmarks and a list of bounding boxes
    """

    testLandmarkList = OrderedDict()
    img = img[:, :, ::-1]

    bounding_boxes, testLandmarks = detect_faces(img, pnet=net_list[0], rnet=net_list[1], onet=net_list[2],
                                                 min_face_size=min_face_size, thresholds=[0.6, 0.7, 0.85],
                                                 device=device)
    for face in range(len(testLandmarks)):
        i = testLandmarks[face]
        landmarkReshaped = [i[0], i[5], i[1], i[6], i[2], i[7], i[3], i[8], i[4], i[9]]
        landmarkReshaped = np.around(landmarkReshaped).astype(int)
        a = 'face_' + str(face)
        testLandmarkList[a] = landmarkReshaped
    boundingBoxesList = bounding_boxes

    return testLandmarkList, boundingBoxesList

def alignment(src_img, src_pts):
    """
    Generalized alignment function. Makes use of Affine transform
    :param src_img: image to be aligned
    :param src_pts: facial landmarks in src image
    :return: aligned cropped image
    """
    ref_pts = [
        [38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]
    ]
    crop_size = (112, 112)

    src_pts = np.array(src_pts).reshape(5, 2)

    s = np.array(src_pts).astype(np.float32)
    r = np.array(ref_pts).astype(np.float32)

    tfm = get_similarity_transform_for_cv2(s, r)
    face_img = cv2.warpAffine(src_img, tfm, crop_size)
    return face_img

def AlignTestFaces(img, testLandmarkList):
    """
    Given an image with multiple faces and detected landmarks returns the aligned faces as a dictionary
    :param img: image with multiple faces
    :param testLandmarkList: dictionary of landmarks in the image
    :return: dictionary of aligned faces
    """

    alignedImages = OrderedDict()
    for key in testLandmarkList:
        alignedImages[key] = alignment(img, testLandmarkList[key])
    return alignedImages

# The function to detect faces.
@app.route("/detect_face", methods=['POST'])
def face_detection():
    global device
    # Uncomment the following lines before dockerizing
    # Receive JSON data from the request body
    json_data = request.data.decode('utf-8')
    # Deserialize JSON data to ndarray
    img = np.array(json.loads(json_data), dtype=np.uint8)

    # Uncomment the following code to directly test this application
    # image_file = request.files['image'].read()
    # # Convert bytes to NumPy array
    # img_array = np.frombuffer(image_file, np.uint8)
    # # Decode NumPy array into image
    # img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    # Invoke DetectLandmarks function. It will return bounding boxes and landmark points.
    testLandMarkList, testBBList = DetectLandmarks(img, net_list=fd_model, min_face_size=min_face_size, device=device)
    # Assume that our inputs contain only one face.
    # Thereafter, align the faces, and invoke feature extraction.
    AlignedTestFace = AlignTestFaces(img, testLandMarkList)

    # Uncomment the following line to execute the application as a Flask application
    # base_url = 'http://127.0.0.1:5000'
    # Uncomment the following line before dockerizing
    base_url = os.environ.get('FR_URL')
    path = "/recognize_face"
    url = base_url + path

    # Code to send all detected faces to the recognizer at once
    # Convert NumPy arrays to lists (JSON doesn't support NumPy arrays directly)
    for key, value in AlignedTestFace.items():
        AlignedTestFace[key] = value.tolist()

    json_payload = json.dumps(AlignedTestFace).encode('utf-8')
    req = urllib.request.Request(url, data=json_payload, method='POST')
    # Add appropriate headers
    req.add_header('Content-Type', 'application/json')

    # Make the request
    response = urllib.request.urlopen(req)
    # Read response data
    response_data = response.read()
    return json.loads(response_data)

if __name__ == "__main__":
    # Load the Face Detection model
    device = torch.device(
        "cuda:0" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    # device = torch.device("cpu")
    fd_model = loadFDModel(device)
    min_face_size = 100
    DEBUG = False
    app.run(host='0.0.0.0', port=4000, threaded=True)