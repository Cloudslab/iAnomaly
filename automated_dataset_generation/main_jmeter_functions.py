import datetime
import time
import paramiko

# Define variables used by main_jmeter_function here
PEM_FILE="../anomaly_detect_key.pem"
JMETER_VM_USER="ubuntu"
JMETER_VM_HOST="172.26.131.241"
PATH_TO_JMETER="./apache-jmeter-5.6.3/bin/jmeter"
RESULTS_FILE="/home/ubuntu/jmeter_tests/results.jtl"

PATH_TO_JMX_FILE="/home/ubuntu/jmeter_tests/test_standalone_preprocessor_parameterize.jmx"

def run_normal_jmeter_test(server_ip,port_num,concurrency,think_time,actual_duration_for_normal_data):
    print("Normal data thread : ", datetime.datetime.now())
    print("""Send a jmeter load to server IP : {0} at port : {1} """.format(server_ip, port_num))
    print("""Execute a normal load of concurrency : {0} and think time : {1} for duration : {2} """.format(concurrency,think_time,actual_duration_for_normal_data))
    # Establish SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(JMETER_VM_HOST, username=JMETER_VM_USER, key_filename=PEM_FILE)

    # Execute JMeter test via SSH
    command = f"{PATH_TO_JMETER} -n -t {PATH_TO_JMX_FILE} -JserverIp={server_ip} -JportNum={port_num} -Jduration={actual_duration_for_normal_data} -Jconcurrency={concurrency} -JthinkTime={think_time} -l {RESULTS_FILE}"
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
    # time.sleep(actual_duration_for_normal_data) # Only to mock
