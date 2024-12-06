# Code to parse the config.yaml
import yaml
import threading
import time
import datetime
from main_jmeter_functions import run_normal_jmeter_test
from secondary_jmeter_functions import run_user_surge
from chaos_mesh_functions import run_cpu_stress_experiment,run_memory_stress_experiment,run_network_delay_experiment
from pixie_monitor_client import run_monitor_orchestrator

def run_anomaly_injection_scenarios(server_ip,port_num,deployment_name,normal_data_duration,slack_duration,anomalies):
    sleep_duration1 = normal_data_duration+slack_duration
    time.sleep(sleep_duration1)
    print("Anomaly injection thread (start) : ", datetime.datetime.now())
    for anomaly in anomalies:
        anomaly_type = anomaly['type']
        duration = anomaly['duration']
        if anomaly_type in ["user-surge-spike","user-surge-step"]:
            run_user_surge(server_ip,port_num,anomaly_type,duration,anomaly['concurrency'])
        elif anomaly_type == "chaosmesh_yamls":
            run_cpu_stress_experiment(deployment_name, duration, anomaly['load'])
        elif anomaly_type == "memory-stress":
            run_memory_stress_experiment(deployment_name, duration, anomaly['size'])
        elif anomaly_type == "network-delay":
            run_network_delay_experiment(deployment_name, duration, anomaly['latency'])
        time.sleep(anomaly['cool_down_period'])
        print("Anomaly injection thread (end of cooldown) : ", datetime.datetime.now())
    time.sleep(slack_duration)
    print("Anomaly injection thread (end) : ", datetime.datetime.now())

# Main method
if __name__ == "__main__":
    # Load YAML configuration
    with open('config2.yaml', 'r') as file:
        config = yaml.safe_load(file)

    # Extract details
    # Deployment info
    deployment_name = config['deployment']['deployment_name']
    pod_id = config['deployment']['pod_id']
    server_ip = config['deployment']['server_ip']
    port_num = config['deployment']['port_num']
    # Normal data
    normal_data = config['normal_data']
    # Anomaly data
    anomalies = config['anomaly_data']['anomalies']

    # Analyse the yaml to identify the total duration for data collection
    slack_duration = 1 #5*60
    actual_duration_for_normal_data = normal_data['duration'] + (2 * slack_duration)
    for anomaly in anomalies:
        actual_duration_for_normal_data += anomaly['duration']+anomaly['cool_down_period']

    # Start a thread which generates normal data for the duration derived at actual_duration_for_normal_data
    normal_load_thread = threading.Thread(target=run_normal_jmeter_test, args=(server_ip,port_num,normal_data['concurrency'],normal_data['think_time'],actual_duration_for_normal_data))
    # Start a thread which collects metrics at the end of normal_data['duration'] and then at the end of actual_duration_for_normal_data
    # monitoring_data_collection_thread = threading.Thread(target=run_monitoring_data_collection, args=(deployment_name+'-'+pod_id,normal_data['duration'],actual_duration_for_normal_data-normal_data['duration']))
    # Start a thread which starts injecting anomalies at the end of normal_data['duration']+slack_duration, and then injects each anomaly for the duration and sleeps for cool_down_period
    anomaly_injection_thread = threading.Thread(target=run_anomaly_injection_scenarios, args=(server_ip,port_num,deployment_name,normal_data['duration'],slack_duration,anomalies))
    normal_load_thread.start()
    # monitoring_data_collection_thread.start()
    anomaly_injection_thread.start()
    time.sleep(normal_data['duration'])
    print("Monitoring thread (collect normal data) : ", datetime.datetime.now())
    print("""Collect normal data from pod : {0}""".format(deployment_name+'-'+pod_id))
    run_monitor_orchestrator(deployment_name+'-'+pod_id,normal_data['duration'],"normal")
    time.sleep(actual_duration_for_normal_data-normal_data['duration'])
    print("Monitoring thread (collect anomaly data) : ", datetime.datetime.now())
    print("""Collect anomaly data from pod : {0}""".format(deployment_name+'-'+pod_id))
    run_monitor_orchestrator(deployment_name+'-'+pod_id,actual_duration_for_normal_data-normal_data['duration'],"anomaly")
    normal_load_thread.join()
    # monitoring_data_collection_thread.join()
    anomaly_injection_thread.join()

    print("debug")