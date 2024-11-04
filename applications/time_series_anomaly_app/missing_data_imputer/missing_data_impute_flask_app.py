import json

from flask import Flask, request, jsonify
import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer

app = Flask(__name__)

@app.route('/impute_missing_data', methods=['POST'])
def impute_missing_data():
    str_data = request.get_json()
    data = json.loads(str_data)
    df = pd.DataFrame(data)

    # Initialize IterativeImputer
    imputer = IterativeImputer(max_iter=10, random_state=0)
    # Fit and transform the data
    imputed_data = imputer.fit_transform(df)
    # Convert the result back to a DataFrame
    imputed_df = pd.DataFrame(imputed_data, columns=df.columns)
    # Return the imputed DataFrame as JSON
    return jsonify(imputed_df.to_json(orient='records'))
