import paramiko
import time

# Define variables used by secondary_jmeter_function here
PEM_FILE="../anomaly_detect_key.pem"
JMETER_VM_USER="ubuntu"
JMETER_VM_HOST="172.26.134.46" # Replace with IP of secondary Jmeter VM
PATH_TO_JMETER="./apache-jmeter-5.6.3/bin/jmeter"
RESULTS_FILE="/home/ubuntu/jmeter_tests/results.jtl"

PATH_TO_SPIKE_JMX_FILE="/home/ubuntu/jmeter_tests/segment-user-surge-spike.jmx"
PATH_TO_STEP_JMX_FILE="/home/ubuntu/jmeter_tests/segment-user-surge-step.jmx" # Replace with path to step jmx file

def run_user_surge(server_ip,port_num,anomaly_type,duration,concurrency):
    if anomaly_type == "user-surge-spike":
        # startup_time = 0 # Can set this in jmx
        hold_load = duration
        # shutdown_time = 0 # Can set this in jmx
        print("""Send a jmeter load to server IP : {0} at port : {1} """.format(server_ip, port_num))
        # Refer to PATH_TO_SPIKE_JMX_FILE
        print("""Insert user surge spike of concurrency : {0} for duration : {1} """.format(concurrency, hold_load))
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(JMETER_VM_HOST, username=JMETER_VM_USER, key_filename=PEM_FILE)

        # Execute JMeter test via SSH
        command = f"{PATH_TO_JMETER} -n -t {PATH_TO_SPIKE_JMX_FILE} -JserverIp={server_ip} -JportNum={port_num} -Jconcurrency={concurrency} -JholdLoad={hold_load} -l {RESULTS_FILE}"
        stdin, stdout, stderr = ssh.exec_command(command)
        # Wait for the command to complete
        exit_status = stdout.channel.recv_exit_status()

        # Check the exit status
        if exit_status == 0:
            print("JMeter test completed successfully.")
            print(stdout.read().decode())
        else:
            print(f"JMeter test failed with exit status {exit_status}.")
            print(stderr.read().decode())

        ssh.close()

        print("completed")
        # time.sleep(hold_load) # Only to mock
    elif anomaly_type == "user-surge-step":
        ramp_time = duration * (5 / 12)
        hold_load = duration * (1 / 6)
        print("""Send a jmeter load to server IP : {0} at port : {1} """.format(server_ip, port_num))
        # Refer to PATH_TO_STEP_JMX_FILE
        print("""Startup time of {0}""".format(ramp_time))
        print("""High load of concurrency : {0} for duration : {1} """.format(concurrency, hold_load))
        print("""Shutdown time of {0}""".format(ramp_time))
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(JMETER_VM_HOST, username=JMETER_VM_USER, key_filename=PEM_FILE)

        # Execute JMeter test via SSH
        command = f"{PATH_TO_JMETER} -n -t {PATH_TO_STEP_JMX_FILE} -JserverIp={server_ip} -JportNum={port_num} -Jconcurrency={concurrency} -JholdLoad={hold_load} -JrampTime={ramp_time} -l {RESULTS_FILE}"
        stdin, stdout, stderr = ssh.exec_command(command)
        # Wait for the command to complete
        exit_status = stdout.channel.recv_exit_status()

        # Check the exit status
        if exit_status == 0:
            print("JMeter test completed successfully.")
            print(stdout.read().decode())
        else:
            print(f"JMeter test failed with exit status {exit_status}.")
            print(stderr.read().decode())

        ssh.close()

        print("completed")
        # time.sleep(hold_load+(2*ramp_time))  # Only to mock
