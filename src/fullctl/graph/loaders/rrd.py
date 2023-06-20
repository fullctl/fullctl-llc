try:
    import rrdtool
except ImportError:
    rrdtool = None

import json

def load_rrd_file(file_path):
    """
    Load RRD file and return data as a list of dictionaries.
    """
    data = rrdtool.fetch(file_path, "AVERAGE", "-s", "now-1d", "-e", "now")
    start, end, step = data[0]
    values = data[2]

    result = []
    for row in values:
        timestamp = start
        bps_in, bps_out = row
        result.append({
            "timestamp": timestamp,
            "bps_in": bps_in,
            "bps_out": bps_out,
        })
        start += step

    return result

def rrd_data_to_json(rrd_data):
    """
    Convert RRD data to JSON format.
    """
    return json.dumps(rrd_data)