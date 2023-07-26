try:
    import rrdtool
except ImportError:
    rrdtool = None

import json
import os
import time


def load_rrd_file(file_path, start_time=None, duration=86400, resolution=300):
    """
    Load RRD file and return data as a list of dictionaries.

    :param file_path: Path to the RRD file.
    :param start_time: The start time for fetching data (timestamp). Defaults to now.
    :param duration: The duration for fetching data in seconds. Defaults to 24 hours (86400 seconds).
    """
    # Set the default start time to now if not provided
    if start_time is None:
        start_time = int(time.time())

    # Calculate the end time based on the start time and duration
    end_time = start_time - duration

    # Fetch data from the RRD file for the specified time range
    data_avg = rrdtool.fetch(
        file_path,
        "AVERAGE",
        "-s",
        str(end_time),
        "-e",
        str(start_time),
        "-r",
        str(resolution),
    )
    data_max = rrdtool.fetch(
        file_path,
        "MAX",
        "-s",
        str(end_time),
        "-e",
        str(start_time),
        "-r",
        str(resolution),
    )

    start_avg, end_avg, step_avg = data_avg[0]
    start_max, end_max, step_max = data_max[0]
    values_avg = data_avg[2]
    values_max = data_max[2]

    result = []
    for row_avg, row_max in zip(values_avg, values_max):
        timestamp = start_avg
        bps_in, bps_out, _, _ = row_avg
        _, _, bps_in_max, bps_out_max = row_max
        result.append(
            {
                "timestamp": timestamp,
                "bps_in": bps_in,
                "bps_out": bps_out,
                "bps_in_max": bps_in_max,
                "bps_out_max": bps_out_max,
            }
        )
        start_avg += step_avg

    return result


def rrd_data_to_json(rrd_data):
    """
    Convert RRD data to JSON format.
    """
    return json.dumps(rrd_data)


def get_last_update_time(file_path):
    """
    Get the most recent timestamp in the RRD file.

    :param file_path: Path to the RRD file.
    :return: The most recent timestamp in the RRD file.
    """

    if not os.path.exists(file_path):
        return None

    rrd_info = rrdtool.info(file_path)
    return int(rrd_info["last_update"])


def update_rrd_from_log(file_path, log_file_path, last_update_time=None):
    """
    Update an RRD file with data from a plain text log file.

    :param file_path: Path to the RRD file.
    :param log_file_path: Path to the plain text log file.
    :param last_update_time: The most recent timestamp in the RRD file. If not provided, the function will fetch it automatically.
    """
    # Read log lines from the log file
    with open(log_file_path) as log_file:
        log_lines = log_file.readlines()

    # reverse the log lines so that the oldest log line is first
    log_lines.reverse()

    # Check if RRD file exists, if not create it
    if not os.path.exists(file_path):
        # Get the timestamp of the first log line
        first_log_line = log_lines[0]
        first_timestamp = int(first_log_line.split()[0])

        # Create the RRD file with the first timestamp as the start time
        create_rrd_file(file_path, first_timestamp)

    # Fetch the most recent timestamp in the RRD file if not provided
    if last_update_time is None:
        last_update_time = get_last_update_time(file_path)

    # Process each log line and update the RRD file
    for log_line in log_lines:
        update_rrd(file_path, log_line, last_update_time)


def stream_log_lines_to_rrd(file_path, log_stream, last_update_time=None):
    """
    Stream log lines from a file-like object and update the RRD file.

    :param file_path: Path to the RRD file.
    :param log_stream: A file-like object that yields log lines.
    :param last_update_time: The most recent timestamp in the RRD file. If not provided, the function will fetch it automatically.
    """
    # Check if RRD file exists, if not create it
    if not os.path.exists(file_path):
        create_rrd = True
    else:
        create_rrd = False

    # Fetch the most recent timestamp in the RRD file if not provided
    if last_update_time is None:
        last_update_time = get_last_update_time(file_path)

    # Process each log line from the stream and update the RRD file
    for log_line in log_stream:
        if create_rrd:
            create_rrd_file(file_path, int(log_line.split()[0]))
            create_rrd = False

        update_rrd(file_path, log_line)


def create_rrd_file(file_path, start_time, heartbeat=90000):
    """
    Create an RRD file with the required data sources and archives.

    The RRD file will have the following configuration:
    - Step: 300 seconds (5 minutes) between data points.
    - Data Sources:
        - bps_in: GAUGE, Heartbeat 600, Min 0, Max U (unknown).
        - bps_out: GAUGE, Heartbeat 600, Min 0, Max U (unknown).
        - bps_in_max: GAUGE, Heartbeat 600, Min 0, Max U (unknown).
        - bps_out_max: GAUGE, Heartbeat 600, Min 0, Max U (unknown).
    - Round Robin Archives:
        - AVERAGE, XFF 0.5, 1 PDP per CDP, 288 CDPs (1 day of data with 5-minute resolution).
        - AVERAGE, XFF 0.5, 3 PDPs per CDP, 672 CDPs (7 days of data with 15-minute resolution).
        - AVERAGE, XFF 0.5, 6 PDPs per CDP, 336 CDPs (7 days of data with 30-minute resolution).
        - AVERAGE, XFF 0.5, 24 PDPs per CDP, 720 CDPs (30 days of data with 2-hour resolution).
        - AVERAGE, XFF 0.5, 12 PDPs per CDP, 744 CDPs (31 days of data with 1-hour resolution).
        - AVERAGE, XFF 0.5, 72 PDPs per CDP, 1460 CDPs (365 days of data with 6-hour resolution).
        - MAX, XFF 0.5, 1 PDP per CDP, 288 CDPs (1 day of data with 5-minute resolution).
        - MAX, XFF 0.5, 3 PDPs per CDP, 672 CDPs (7 days of data with 15-minute resolution).
        - MAX, XFF 0.5, 6 PDPs per CDP, 336 CDPs (7 days of data with 30-minute resolution).
        - MAX, XFF 0.5, 24 PDPs per CDP, 720 CDPs (30 days of data with 2-hour resolution).
        - MAX, XFF 0.5, 12 PDPs per CDP, 744 CDPs (31 days of data with 1-hour resolution).
        - MAX, XFF 0.5, 72 PDPs per CDP, 1460 CDPs (365 days of data with 6-hour resolution).
        - MAX, XFF 0.5, 72 PDPs per CDP, 1460 CDPs (365 days of data with 6-hour resolution).

    :param file_path: Path to the RRD file.
    :param start_time: The start time of the RRD file.
    """
    rrdtool.create(
        file_path,
        "--start",
        str(start_time - 1),  # Subtract 1 to ensure the first log line can be added
        "--step",
        "300",
        f"DS:bps_in:GAUGE:{heartbeat}:0:U",
        f"DS:bps_out:GAUGE:{heartbeat}:0:U",
        f"DS:bps_in_max:GAUGE:{heartbeat}:0:U",  # Add bps_in_max data source
        f"DS:bps_out_max:GAUGE:{heartbeat}:0:U",  # Add bps_out_max data source
        "RRA:AVERAGE:0.5:1:288",
        "RRA:AVERAGE:0.5:3:672",
        "RRA:AVERAGE:0.5:6:336",
        "RRA:AVERAGE:0.5:24:720",
        "RRA:AVERAGE:0.5:12:744",
        "RRA:AVERAGE:0.5:72:1460",
        "RRA:AVERAGE:0.5:288:7300",
        "RRA:MAX:0.5:1:288",
        "RRA:MAX:0.5:3:672",
        "RRA:MAX:0.5:6:336",
        "RRA:MAX:0.5:24:720",
        "RRA:MAX:0.5:12:744",
        "RRA:MAX:0.5:72:1460",
        "RRA:MAX:0.5:288:7300",
    )


def update_rrd(file_path, log_line, last_update_time=None, is_bytes=True):
    """
    Update the RRD file with data from a log line.

    :param file_path: Path to the RRD file.
    :param log_line: A single log line containing the data.
    :param last_update_time: The most recent timestamp in the RRD file. If not provided, the function will update the RRD file without checking the timestamp.
    :param is_bytes: A boolean value indicating whether the data is in bytes. If False, the data will be converted to bits.
    """
    # Parse log line
    timestamp, avg_bytes_in, avg_bytes_out, max_bytes_in, max_bytes_out = map(
        int, log_line.split()[:5]
    )

    # Convert bytes to bits if necessary
    if is_bytes:
        avg_bytes_in, avg_bytes_out, max_bytes_in, max_bytes_out = map(
            lambda x: x * 8, [avg_bytes_in, avg_bytes_out, max_bytes_in, max_bytes_out]
        )

    # Check if the timestamp is newer than the most recent data in the RRD file
    if last_update_time is None or timestamp > last_update_time:
        rrdtool.update(
            file_path,
            f"{timestamp}:{avg_bytes_in}:{avg_bytes_out}:{max_bytes_in}:{max_bytes_out}",
        )


def aggregate_rrd_files(rrd_files, output_file):
    """
    Aggregate multiple RRD files into one.

    :param rrd_files: A list of paths to the RRD files to be aggregated.
    :param output_file: Path to the output RRD file.
    """
    # Define the durations for each RRA in descending order
    durations = [86400 * 365 * 19, 86400 * 335, 86400 * 30, 86400 * 6, 86400]

    # Initialize an empty dictionary to store the aggregated data
    aggregated_data = {}

    # Loop through each RRD file
    for rrd_file in rrd_files:
        start_time = None
        idx = 0

        # Loop through each duration
        for duration in durations:
            try:
                start_time = int(time.time()) - durations[idx + 1]
            except IndexError:
                start_time = None

            # Load the RRD file data for the current duration
            rrd_data = load_rrd_file(rrd_file, start_time=start_time, duration=duration)

            # Add the RRD data to the aggregated data
            for data in rrd_data:
                if data["bps_in"] is None:
                    continue

                timestamp = data["timestamp"]

                if timestamp not in aggregated_data:
                    aggregated_data[timestamp] = {"timestamp": timestamp}
                # Merge data points with the same timestamp by adding the values
                for key in data:
                    if key in ["bps_in", "bps_out", "bps_in_max", "bps_out_max"]:
                        if key not in aggregated_data[timestamp]:
                            aggregated_data[timestamp][key] = 0
                        aggregated_data[timestamp][key] += int(data[key])

            # Update the last update time for the next duration
            last_update_time = start_time

            idx += 1

    # print(f"Aggregated {len(rrd_files)} RRD files into {len(aggregated_data)} data points.")

    # Sort the aggregated data by timestamp
    aggregated_data = sorted(aggregated_data.values(), key=lambda x: x["timestamp"])

    # Create the output RRD file
    if not os.path.exists(output_file):
        create_rrd_file(output_file, aggregated_data[0]["timestamp"] + 1)

    # Fetch the most recent timestamp in the RRD file if not provided
    last_update_time = get_last_update_time(output_file)

    # Update the output RRD file with the aggregated data
    for data in aggregated_data:
        update_rrd(
            output_file,
            f"{data['timestamp']} {int(data['bps_in'])} {int(data['bps_out'])} {int(data['bps_in_max'])} {int(data['bps_out_max'])}",
            last_update_time=last_update_time,
            # We are aggregating from existing rrd files, which already store as bits
            is_bytes=False,
        )
