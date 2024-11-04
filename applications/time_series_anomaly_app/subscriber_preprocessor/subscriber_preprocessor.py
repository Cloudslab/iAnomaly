import pandas as pd
from kafka import KafkaConsumer
import json
import random
import requests
import os
import numpy as np

# Function to create a Kafka consumer
def create_kafka_consumer(bootstrap_servers, topic, group_id):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='earliest',  # Start reading at the earliest message
        enable_auto_commit=True,
        group_id=group_id,
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    return consumer

class ReservoirSampler:
    def __init__(self, size):
        self.size = size
        self.reservoir = []
        self.count = 0

    def add(self, item):
        self.count += 1
        if len(self.reservoir) < self.size:
            self.reservoir.append(item)
        else:
            # Randomly replace an item in the reservoir with the new item
            s = random.randint(0, self.count - 1)
            if s < self.size:
                self.reservoir[s] = item

    def get_mu_sigma(self):
        # Form a dataframe from reservoir
        reservoir_df = pd.DataFrame(self.reservoir)
        # Obtain mu and sigma from each attribute of reservoir_df
        reservoir_means = reservoir_df[['in_avg_response_time', 'in_throughput', 'in_progress_requests', 'http_error_count', 'ballerina_error_count', 'cpu', 'memory', 'cpuPercentage', 'memoryPercentage']].mean()
        reservoir_stds = reservoir_df[['in_avg_response_time', 'in_throughput', 'in_progress_requests', 'http_error_count', 'ballerina_error_count', 'cpu', 'memory', 'cpuPercentage', 'memoryPercentage']].std()
        # Merge reservoir_means and reservoir_stds, and form mean_std_dict
        mean_std_dict = {col: {'mean': reservoir_means[col], 'std': reservoir_stds[col]} for col in reservoir_means.index}
        return mean_std_dict

# Function to consume messages from Kafka topic
def consume_from_kafka(consumer, reservoir_sampler):
    window = []
    window_size = 10

    # Define the URL of the Anomaly Detector Flask app and Missing data imputer service.
    ad_base_url = os.environ.get('AD_URL')
    ad_path = "/detect_anomalies"
    ad_url = ad_base_url + ad_path
    # ad_url = 'http://127.0.0.1:5000/detect_anomalies' # Replace url based on AD (gunicorn : 8080, flask : 5000)
    mdi_base_url = os.environ.get('MDI_URL')
    mdi_path = "/impute_missing_data"
    imputation_url = mdi_base_url + mdi_path
    # imputation_url = 'http://127.0.0.1:5002/impute_missing_data'

    for message in consumer:
        # print(f"Received message: {message.value}")
        reservoir_sampler.add(message.value)

        if len(window) < window_size:
            window.append(message.value)
        else:
            # Form a dataframe by using the dictionaries in window
            df = pd.DataFrame(window)
            # Drop datetime and timestamp from df
            df = df.drop(['datetime','timestamp'], axis=1)
            # Check for missing values in df. If there are any missing values, send that for imputation
            if df.isna().sum().sum()>0:
                # Send a POST request to the Imputation microservice
                response = requests.post(imputation_url, json=df.to_json(orient='records'))

                # Check if the imputation was successful
                if response.status_code == 200:
                    imputed_data = response.json()
                    df = pd.read_json(imputed_data)
                else:
                    print('Failed to impute missing data:', response.status_code)
                    continue

            mean_std_dict = reservoir_sampler.get_mu_sigma()

            # Standardize the df
            for col in mean_std_dict.keys():
                mean = mean_std_dict[col]['mean']
                std = mean_std_dict[col]['std']
                df[col] = (df[col] - mean) / std

            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            # Fill NaN values with 0
            df = df.fillna(0)

            # Send a POST request to the AD Flask app
            response = requests.post(ad_url, json=df.to_json(orient='records'))

            # Check the status code of the response
            if response.status_code == 200:
                print('Response:', response.json())
            else:
                print('Failed to retrieve data:', response.status_code)

            window.clear()

# Main function
def main():
    kafka_bootstrap_servers = ['kafka-service.default.svc.cluster.local:9092'] #['localhost:9092']
    kafka_topic = 'sensor_1'
    kafka_group_id = 'group_1'
    reservoir_size = 5

    # Create Kafka consumer
    consumer = create_kafka_consumer(kafka_bootstrap_servers, kafka_topic, kafka_group_id)

    # Create a reservoir sampler
    reservoir_sampler = ReservoirSampler(reservoir_size)

    # Consume messages from Kafka topic
    consume_from_kafka(consumer, reservoir_sampler)

if __name__ == '__main__':
    main()
