import time

import pxapi
import pandas as pd


def compose_pxl_script(query_type, pod_name, duration):
    if query_type == 'latency':
        LATENCY_SCRIPT = """
import px
ns_per_ms = 1000 * 1000
ns_per_s = 1000 * ns_per_ms
# Window size to use on time_ column for bucketing.
window_ns = px.DurationNanos(10 * ns_per_s)

df = px.DataFrame(table='http_events', start_time="{0}")
df.failure = df.resp_status >= 400

filter_out_conds = ((df.req_path != '/healthz') and (df.req_path != '/readyz')) and (df['remote_addr'] != '-')
df = df[filter_out_conds]

df.pod = df.ctx['pod']
df = df[df.pod == "default/{1}"]

# Filter only to inbound pod traffic (server-side).
# Don't include traffic initiated by this pod to an external location.
df = df[df.trace_role == 2]

df.timestamp = px.bin(df.time_, window_ns)
df = df.groupby(['timestamp']).agg(
    latency_quantiles=('latency', px.quantiles)
)
df.latency_p50 = px.DurationNanos(px.floor(px.pluck_float64(df.latency_quantiles, 'p50')))
df.latency_p90 = px.DurationNanos(px.floor(px.pluck_float64(df.latency_quantiles, 'p90')))
df.latency_p99 = px.DurationNanos(px.floor(px.pluck_float64(df.latency_quantiles, 'p99')))
df.time_ = df.timestamp
df = df.drop(['latency_quantiles', 'timestamp'])
px.display(df, 'latency_table')
""".format(duration, pod_name)
        return LATENCY_SCRIPT
    elif query_type == 'network':
        NETWORK_SCRIPT = """
import px
ns_per_ms = 1000 * 1000
ns_per_s = 1000 * ns_per_ms
# Window size to use on time_ column for bucketing.
window_ns = px.DurationNanos(10 * ns_per_s)
df = px.DataFrame(table='network_stats', start_time="{0}")
df = df[df.ctx['pod'] == "default/{1}"]
df.timestamp = px.bin(df.time_, window_ns)

# First calculate network usage by node over all windows.
# Data is sharded by Pod in network_stats.
df = df.groupby(['timestamp', 'pod_id']).agg(
    rx_bytes_end=('rx_bytes', px.max),
    rx_bytes_start=('rx_bytes', px.min),
    tx_bytes_end=('tx_bytes', px.max),
    tx_bytes_start=('tx_bytes', px.min),
)

# Calculate the network statistics rate over the window.
# We subtract the counter value at the beginning ('_start')
# from the value at the end ('_end').
df.rx_bytes_per_ns = (df.rx_bytes_end - df.rx_bytes_start) / window_ns
df.tx_bytes_per_ns = (df.tx_bytes_end - df.tx_bytes_start) / window_ns

# Add up the network values per node.
df = df.groupby(['timestamp']).agg(
    rx_bytes_per_ns=('rx_bytes_per_ns', px.sum),
    tx_bytes_per_ns=('tx_bytes_per_ns', px.sum),
)
df.time_ = df.timestamp
df = df.drop(['timestamp'])
px.display(df, 'network_table')
""".format(duration, pod_name)
        return NETWORK_SCRIPT
    elif query_type == 'resource':
        RESOURCE_SCRIPT = """
import px
ns_per_ms = 1000 * 1000
ns_per_s = 1000 * ns_per_ms
# Window size to use on time_ column for bucketing.
window_ns = px.DurationNanos(10 * ns_per_s)
df = px.DataFrame(table='process_stats', start_time="{0}")
df = df[df.ctx['pod'] == "default/{1}"]
df.timestamp = px.bin(df.time_, window_ns)
df.container = df.ctx['container_name']

# First calculate CPU usage by process (UPID) in each k8s_object
# over all windows.
df = df.groupby(['upid', 'container', 'timestamp']).agg(
    rss=('rss_bytes', px.mean),
    vsize=('vsize_bytes', px.mean),
    # The fields below are counters, so we take the min and the max to subtract them.
    cpu_utime_ns_max=('cpu_utime_ns', px.max),
    cpu_utime_ns_min=('cpu_utime_ns', px.min),
    cpu_ktime_ns_max=('cpu_ktime_ns', px.max),
    cpu_ktime_ns_min=('cpu_ktime_ns', px.min),
    rchar_bytes_max=('rchar_bytes', px.max),
    rchar_bytes_min=('rchar_bytes', px.min),
    wchar_bytes_max=('wchar_bytes', px.max),
    wchar_bytes_min=('wchar_bytes', px.min),
)


# Next calculate cpu usage and memory stats per window.
df.cpu_utime_ns = df.cpu_utime_ns_max - df.cpu_utime_ns_min
df.cpu_ktime_ns = df.cpu_ktime_ns_max - df.cpu_ktime_ns_min
df.total_disk_read_throughput = (df.rchar_bytes_max - df.rchar_bytes_min) / window_ns
df.total_disk_write_throughput = (df.wchar_bytes_max - df.wchar_bytes_min) / window_ns

# Then aggregate process individual process metrics.
df = df.groupby(['timestamp', 'container']).agg(
    cpu_ktime_ns=('cpu_ktime_ns', px.sum),
    cpu_utime_ns=('cpu_utime_ns', px.sum),
    total_disk_read_throughput=('total_disk_read_throughput', px.sum),
    total_disk_write_throughput=('total_disk_write_throughput', px.sum),
    rss=('rss', px.sum),
    vsize=('vsize', px.sum),
)

# Finally, calculate total (kernel + user time)  percentage used over window.
df.cpu_usage = px.Percent((df.cpu_ktime_ns + df.cpu_utime_ns) / window_ns)
df.time_ = df.timestamp
df = df.drop(['cpu_ktime_ns', 'cpu_utime_ns', 'timestamp'])
px.display(df, 'resource_table')
""".format(duration, pod_name)
        return RESOURCE_SCRIPT
    elif query_type == 'throughput_error':
        THROUGHPUT_ERROR_SCRIPT = """
import px
ns_per_ms = 1000 * 1000
ns_per_s = 1000 * ns_per_ms
# Window size to use on time_ column for bucketing.
window_ns = px.DurationNanos(10 * ns_per_s)

df = px.DataFrame(table='http_events', start_time="{0}")
df.failure = df.resp_status >= 400

filter_out_conds = ((df.req_path != '/healthz') and (df.req_path != '/readyz')) and (df['remote_addr'] != '-')
df = df[filter_out_conds]

df.pod = df.ctx['pod']
df = df[df.pod == "default/{1}"]

# Filter only to inbound pod traffic (server-side).
# Don't include traffic initiated by this pod to an external location.
df = df[df.trace_role == 2]

df.container = df.ctx['container']
df.timestamp = px.bin(df.time_, window_ns)
df = df.groupby(['timestamp', 'container']).agg(
    error_rate_per_window=('failure', px.mean),
    throughput_total=('latency', px.count)
)

# Format the result of LET aggregates into proper scalar formats and
# time series.
df.request_throughput = df.throughput_total / window_ns
df.errors_per_ns = df.error_rate_per_window * df.request_throughput / px.DurationNanos(1)
df.time_ = df.timestamp
df = df.drop(['error_rate_per_window','throughput_total','timestamp'])
px.display(df, 'throughput_error_table')
""".format(duration, pod_name)
        return THROUGHPUT_ERROR_SCRIPT


def run_monitor_orchestrator(pod_name, duration, data_type):
    # Create a Pixie client.
    px_client = pxapi.Client(token="px-api-3a43ec3e-5d5c-47b4-9c33-29f22335cd46")  # Use px api-key create to identify API key

    # Connect to cluster.
    conn = px_client.connect_to_cluster("9ee3ab1a-dcbc-47e7-9859-2397c9edd35e")  # Use px get viziers to identify cluster ID

    query_types = ['latency', 'network', 'resource', 'throughput_error']
    duration = int(duration / 60)

    for query_type in query_types:
        # Execute the PxL script.
        # Convert duration to minutes before sending
        PXL_SCRIPT = compose_pxl_script(query_type, pod_name, "-" + str(duration) + "m")
        script = conn.prepare_script(PXL_SCRIPT)
        if query_type == 'latency':
            d = {'latency_p50': [], 'latency_p90': [], 'latency_p99': [], 'time_': []}
            table_name = "latency_table"
        elif query_type == 'network':
            d = {'rx_bytes_per_ns': [], 'tx_bytes_per_ns': [], 'time_': []}
            table_name = "network_table"
        elif query_type == 'resource':
            d = {'container': [], 'total_disk_read_throughput': [], 'total_disk_write_throughput': [], 'rss': [], 'vsize': [], 'cpu_usage': [], 'time_': []}
            table_name = "resource_table"
        elif query_type == 'throughput_error':
            d = {'container': [], 'request_throughput': [], 'errors_per_ns': [], 'time_': []}
            table_name = "throughput_error_table"

        for row in script.results(table_name):
            # Populate final_df with values from the row
            for k in d.keys():
                d[k].append(row[k])

        final_df = pd.DataFrame(data=d)
        final_df = final_df.sort_values('time_')

        final_df.to_csv("collected_metric_dfs/" + data_type + '_' + query_type + "_timeseries.csv", index=False)
