import random
import time

__all__ = ["port_traffic"]


def generate_natural_traffic(min_value, max_value, num_points, peak_indices):
    """
    Generate natural traffic data with specified peaks.
    """
    traffic_data = [random.randint(min_value, max_value) for _ in range(num_points)]

    for peak_index in peak_indices:
        peak_value = random.randint(max_value, max_value * 2)
        traffic_data[peak_index] = peak_value

    for i in range(1, num_points):
        traffic_data[i] = int(traffic_data[i - 1] * 0.9 + traffic_data[i] * 0.1)

    return traffic_data


def port_traffic(num_points, step=3600):
    """
    Generate natural looking data points for port traffic and output a dict.
    """
    result = []
    current_time = int(time.time())
    peak_indices = random.sample(range(num_points), 2)

    bps_in_data = generate_natural_traffic(10**6, 10**11, num_points, peak_indices)
    bps_out_data = generate_natural_traffic(10**6, 10**11, num_points, peak_indices)

    for i in range(num_points):
        timestamp = current_time
        bps_in = bps_in_data[i]
        bps_out = bps_out_data[i]
        result.append(
            {
                "timestamp": timestamp,
                "bps_in": bps_in,
                "bps_out": bps_out,
                "bps_in_max": bps_in,
                "bps_out_max": bps_out,
            }
        )
        current_time -= step

    return result
