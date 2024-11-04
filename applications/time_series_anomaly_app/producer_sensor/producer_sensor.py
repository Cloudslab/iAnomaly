import pandas as pd
from kafka import KafkaProducer
import json
import random
import numpy as np

# Function to read CSV file and return it as a DataFrame
def read_csv(file_path):
    df = pd.read_csv(file_path)
    # Drop the is_anomaly attribute
    df = df.drop(['is_anomaly'], axis=1)
    return df

# Function to create a Kafka producer
def create_kafka_producer(bootstrap_servers):
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    return producer

# Function to send data to Kafka topic
def send_to_kafka(producer, topic, data):
    timestamp = 1615551440 # Corresponds to the unix timestamp of the first datetime entry of the anomaly dataset
    while True:
        for index, row in data.iterrows():
            message = row.to_dict()
            message['timestamp'] = timestamp # Add a new timestamp attribute while keeping the existing datetime attribute for double-checking
            # Get a list of keys from the dictionary
            keys = list(message.keys())
            keys = [e for e in keys if e not in ('datetime','timestamp')]
            if random.random() <= 0.05:
                # Drop few values from the row
                # Randomly determine the number of values to replace
                replace_count = random.randint(1, len(keys)//2)
                # Randomly select keys to replace with N/A
                replace_keys = random.sample(keys, replace_count)
                # Replace the selected keys' values with N/A
                for key in replace_keys:
                    message[key] = np.nan
            timestamp += 10
            producer.send(topic, message)
            producer.flush()  # Ensure the message is sent

# Main function
def main():
    csv_file_path = 'anomaly_data.csv' # service_chain_cpu_hog_step
    kafka_bootstrap_servers = ['kafka-service.default.svc.cluster.local:9092'] # ['localhost:9092']
    kafka_topic = 'sensor_1'

    # Read CSV data while dropping is_anomaly attribute
    data = read_csv(csv_file_path)

    # Create Kafka producer
    producer = create_kafka_producer(kafka_bootstrap_servers)

    # Send data to Kafka topic
    send_to_kafka(producer, kafka_topic, data)

if __name__ == '__main__':
    main()
