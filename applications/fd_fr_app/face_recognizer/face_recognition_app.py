import json
from flask import Flask, request, jsonify
import numpy as np
import torch
from src.net_arc import Backbone
from datetime import datetime
import mysql.connector

app = Flask(__name__)

def loadFRModel(path, device='cpu'):
    """
    Loads the model from the path to cuda and sets to eval mode
    :param model: Path to the trained FR model
    :return: NN for FR
    """
    net = Backbone(num_layers=50, drop_ratio=0.6, mode='ir_se').to(device)
    net.load_state_dict(torch.load(path, map_location=device))
    net.eval()
    return net

def extractMultiFeature(alignedFace, net, device="cpu"):
    """
    Given an aligned face image computes 512 dimensional FR feature for the pic only (used for inference)
    returns [1,512] dimensional tensor corresponding to the image
    :param alignedFace: face image that is aligned to the key points
    :param net: NN trained for FR
    :return: [1,512] dimensional tensor corresponding to the feature
    """

    shape = (112, 112)
    alignedFace = alignedFace[:, :, ::-1]

    alignedFace = alignedFace.transpose(0, 3, 1, 2).astype('float32')
    alignedFace = (alignedFace - 127.5) / 128.0

    img = alignedFace
    with torch.no_grad():
        img = torch.from_numpy(img).to(device)
        output = net(img)

    return output

def identifyMultiFaceWithConfidenceArc(input_feature_vector, feature_vector_matrix):
    if input_feature_vector.shape[0] == 0:
        return {}, {}

    testFeature = input_feature_vector.view(-1, 512, 1, 1)
    dbFeature = feature_vector_matrix.transpose(0, 1).unsqueeze(0)
    diff = testFeature - dbFeature
    dist = torch.sqrt(torch.sum(torch.pow(diff, 2), dim=1))
    min_dist, _ = torch.min(dist, dim=1)
    minimum, min_idx = torch.min(min_dist, dim=1)

    return minimum, min_idx.cpu()

# The function to recognize detected faces.
@app.route("/recognize_face", methods=['POST'])
def face_detection():
    global device
    payload_bytes = request.data

    # Decode the byte literal into a string using UTF-8 encoding
    payload_string = payload_bytes.decode('utf-8')
    # Fix the single quotes into double quotes
    pp_payload_string = payload_string.replace("'", '"')
    # Parse the payload_string as JSON
    AlignedTestFace = json.loads(pp_payload_string)

    inp_faces = np.stack(list(AlignedTestFace.values()))
    feature = extractMultiFeature(inp_faces, fr_model, device=device)
    minimum, uid = identifyMultiFaceWithConfidenceArc(feature, feature_vector_matrix)

    # Write one by one recognized face to the database
    for i in range(minimum.size(0)):
        if minimum[i] < 1:
            # Write the detection to the DB
            now = datetime.now()
            current_time = now.strftime("%Y-%m-%d %H:%M:%S")
            name = vec_keys[uid.tolist()[i]]
            my_cursor = mydb.cursor()
            sqlStuff = "INSERT INTO detections (name, time) VALUES (%s, %s)"
            record1 = (name, current_time)
            my_cursor.execute(sqlStuff, record1)
            mydb.commit()

    # Return a success code to the FD microservice which made the request
    return jsonify(code=0) #, response=uid.tolist())


if __name__ == "__main__":
    # Load the Face Detection model
    device = torch.device(
        "cuda:0" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    # device = torch.device("cpu")
    DEBUG = False

    # Load the Face Recognition model. This has to be moved to a different flask app later.
    fr_model = loadFRModel(path="model/arc_res50.pth", device=device)

    # Load the feature vectors from user database. In this case, we are loading from a json file.
    json_file_path = 'feature_vector_db.json'
    with open(json_file_path, 'r') as j:
        vec = json.loads(j.read())

    feature_vector_matrix = torch.ones(2, 512, 9)
    vec_keys = []
    i = 0
    for key in vec.keys():
        feature_vector_matrix[:, :, i] = torch.from_numpy(np.array(vec[key]))
        vec_keys.append(key)
        i += 1
    feature_vector_matrix = feature_vector_matrix.to(device)

    # Load the database connector
    mydb = mysql.connector.connect(
        host="mysql-service",
        port='3306',
        user="root",
        passwd="abc123",
        database="my_database",
    )

    app.run("0.0.0.0", 5000, threaded=True)