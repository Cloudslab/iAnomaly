import time
import subprocess


def install_helm_chart(chart_name, release_name, parameter1, parameter2):
    command = ['helm', 'install', release_name, chart_name, '--set', parameter1, '--set', parameter2]

    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Helm Chart Installed Successfully!")
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print("Failed to install Helm Chart")
        print(e.stderr.decode())


def uninstall_helm_chart(release_name):
    command = ['helm', 'uninstall', release_name]

    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Helm Chart Uninstalled Successfully!")
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print("Failed to uninstall Helm Chart")
        print(e.stderr.decode())


def run_cpu_stress_experiment(deployment_name, duration, load):
    print("""Install cpu stress helm chart with deployment = {0} and load = {1} as parameters""".format(deployment_name, load))
    install_helm_chart('./chaosmesh_yamls', 'chaosmesh_yamls-release', "appLabel=\"preprocess-svc-deployment\"", "load=" + str(load))
    time.sleep(duration)
    uninstall_helm_chart('chaosmesh_yamls-release')
    print("Uninstall helm chart")


def run_memory_stress_experiment(deployment_name, duration, size):
    print("""Install cpu stress helm chart with deployment = {0} and size = {1} as parameters""".format(deployment_name, size))
    install_helm_chart('./memory-stress', 'memory-stress-release', "appLabel=\"preprocess-svc-deployment\"", "size=" + str(size))
    time.sleep(duration)
    uninstall_helm_chart('memory-stress-release')
    print("Uninstall helm chart")


def run_network_delay_experiment(deployment_name, duration, latency):
    print("""Install cpu stress helm chart with deployment = {0} and latency = {1} as parameters""".format( deployment_name, latency))
    install_helm_chart('./net-delay', 'net-delay-release', "appLabel=\"preprocess-svc-deployment\"", "latency=" + str(latency))
    time.sleep(duration)
    uninstall_helm_chart('net-delay-release')
    print("Uninstall helm chart")


if __name__ == "__main__":
    run_network_delay_experiment("preprocess-svc-deployment", 60, "1100ms")