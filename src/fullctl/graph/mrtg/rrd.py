try:
    import rrdtool
except ImportError:
    rrdtool = None

import json
import os
import time


def load_rrd_file(file_path, start_time=None, duration=86400):
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
        file_path, "AVERAGE", "-s", str(end_time), "-e", str(start_time)
    )
    data_max = rrdtool.fetch(
        file_path, "MAX", "-s", str(end_time), "-e", str(start_time)
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


def create_rrd_file(file_path, start_time):
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
        - AVERAGE, XFF 0.5, 12 PDPs per CDP, 744 CDPs (31 days of data with 1-hour resolution).
        - AVERAGE, XFF 0.5, 72 PDPs per CDP, 1460 CDPs (365 days of data with 6-hour resolution).
        - MAX, XFF 0.5, 1 PDP per CDP, 288 CDPs (1 day of data with 5-minute resolution).
        - MAX, XFF 0.5, 3 PDPs per CDP, 672 CDPs (7 days of data with 15-minute resolution).
        - MAX, XFF 0.5, 12 PDPs per CDP, 744 CDPs (31 days of data with 1-hour resolution).
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
        "DS:bps_in:GAUGE:600:0:U",
        "DS:bps_out:GAUGE:600:0:U",
        "DS:bps_in_max:GAUGE:600:0:U",  # Add bps_in_max data source
        "DS:bps_out_max:GAUGE:600:0:U",  # Add bps_out_max data source
        "RRA:AVERAGE:0.5:1:288",
        "RRA:AVERAGE:0.5:3:672",
        "RRA:AVERAGE:0.5:12:744",
        "RRA:AVERAGE:0.5:72:1460",
        "RRA:MAX:0.5:1:288",  # Add MAX Round Robin Archives
        "RRA:MAX:0.5:3:672",
        "RRA:MAX:0.5:12:744",
        "RRA:MAX:0.5:72:1460",
    )


def update_rrd(file_path, log_line, last_update_time=None):
    """
    Update the RRD file with data from a log line.

    :param file_path: Path to the RRD file.
    :param log_line: A single log line containing the data.
    :param last_update_time: The most recent timestamp in the RRD file. If not provided, the function will update the RRD file without checking the timestamp.
    """
    # Parse log line
    timestamp, avg_bytes_in, avg_bytes_out, max_bytes_in, max_bytes_out = map(
        int, log_line.split()[:5]
    )

    # Check if the timestamp is newer than the most recent data in the RRD file
    if last_update_time is None or timestamp > last_update_time:
        print(
            f"Updating RRD file with data from {timestamp}, avg_bytes_in={avg_bytes_in}, avg_bytes_out={avg_bytes_out}, max_bytes_in={max_bytes_in}, max_bytes_out={max_bytes_out}"
        )
        # Update RRD file with parsed data
        rrdtool.update(
            file_path,
            f"{timestamp}:{avg_bytes_in}:{avg_bytes_out}:{max_bytes_in}:{max_bytes_out}",
        )
    else:
        print(
            f"Skipping RRD update for {timestamp} as it is older than the most recent data in the RRD file ({last_update_time})"
        )
