import pickle
import pandas as pd
from flask import Flask, request, jsonify

app = Flask(__name__)

def loadADModel():
    # Load the model
    with open('models/isolation_forest_model.pkl', 'rb') as file:
        if_model = pickle.load(file)
    return if_model

if_model = loadADModel()

@app.route('/detect_anomalies', methods=['POST'])
def anomaly_detection():
    json_data = request.get_json()
    # Convert JSON data to DataFrame
    X_test = pd.read_json(json_data, orient='records')
    X_test_y_pred = if_model.score_samples(X_test)
    threshold = -0.53
    X_test_is_anomaly = X_test_y_pred < threshold
    if X_test_is_anomaly.any():
        result = True
    else:
        result = False
    return jsonify(result)
