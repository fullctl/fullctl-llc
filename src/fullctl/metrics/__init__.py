"""
Insert and query metrics from Victoriametrics

## Victoriametrics REST API

### Write

https://docs.victoriametrics.com/url-examples/#influxwrite

# curl -d 'measurement,tag1=value1,tag2=value2 field1=123,field2=1.23' -X POST http://localhost:8428/write

### Query

curl http://localhost:8428/prometheus/api/v1/query -d 'query=vm_http_request_errors_total'

## Cluster version query (not yet supported)
curl http://<vmselect>:8481/select/0/prometheus/api/v1/query -d 'query=vm_http_request_errors_total'

## Python API usage

from fullctl.metrics import Metrics
metrics = Metrics("http://victoriametrics:8428")
metrics.write("cpu", {"host": "server1"}, {"usage": 0.5})
metrics.query("cpu_usage")
metrics.query("cpu_usage{host='server1'}")
metrics.query_range("cpu_usage", "-1d", "1h")
"""

import requests

from fullctl.service_bridge.client import url_join

from .schema import Point, QueryResult

try:
    import pytimeparse2
except ImportError:
    pytimeparse2 = None


class Metrics:
    def __init__(self, url: str, auth: tuple[str, str] | None = None):

        """
        Initialize the Metrics client

        Arguments:

        - url: The Victoriametrics URL, e.g. http://victoriametrics:8428
        - auth: Optional. A tuple of (username, password) for basic authentication
        """

        self.url = url
        self.auth = auth

    @classmethod
    def validate_period(cls, period: str | int):
        """
        Validate the period string

        Arguments:

        - period: The period string, e.g. "-1d", "1h", "5m" etc.
          if an integer is passed, it is considered valid as well
          and assumed to be in seconds (or nanoseconds)

        Raises:

        - ValueError: If the period string is invalid
        """

        if pytimeparse2 is None:
            return

        if isinstance(period, int):
            return

        try:
            pytimeparse2.parse(period.lstrip("-"))
        except ValueError:
            raise ValueError(f"Invalid period string: {period}")

    @classmethod
    def build_query_string(
        cls, aggregator: str, metrics: list[str], tags: dict, time_range: str
    ) -> str:
        """
        Build a query string for Victoriametrics

        Arguments:

        - aggregator: The aggregator function, e.g. sum, avg, max, min etc.
        - metrics: A list of metric names
        - tags: A dictionary of tags
        - time_range: The time range, e.g. "-1d", "1h", "5m" etc.

        Returns:

        - The query string (PromQL/MetricsQL)

        Examples:

        ## Query all cpu_usage metrics
        metrics.query("sum", ["cpu_usage"], {}, "-1d")
        > sum({__name__=~"cpu_usage"}[-1d])
        """

        cls.validate_period(time_range)

        # Build the metric selector
        metric_selector = f'__name__=~"{"|".join(metrics)}"'

        # Build the tag selectors
        tag_selectors = ",".join(
            [f'{k}="{v}"' for k, v in tags.items() if v is not None]
        )

        # Combine metric and tag selectors
        selector = (
            f'{{{metric_selector}{", " if tag_selectors else ""}{tag_selectors}}}'
        )

        # Construct the full query
        if aggregator and time_range:
            query = f"{aggregator}({selector}[{time_range}])"
        elif aggregator:
            query = f"{aggregator}({selector})"
        elif time_range:
            query = f"{selector}[{time_range}]"

        return query

    def to_line_protocol(
        self,
        measurement: str,
        tags: dict[str, str | int | float],
        fields: dict[str, int | float],
        timestamp: int | None = None,
    ) -> str:
        tags_str = ",".join([f"{k}={v}" for k, v in tags.items()])
        fields_str = ",".join([f"{k}={v}" for k, v in fields.items()])
        line = f"{measurement},{tags_str} {fields_str}"

        if timestamp is not None:
            # if timestamp is not nanoseconds convert to nanoseconds
            if timestamp < 1e18:  # If timestamp is in seconds or milliseconds
                timestamp = int(timestamp * 1e9)  # Convert to nanoseconds

            line += f" {int(timestamp)}"

        return line

    def write(
        self,
        measurement: str,
        tags: dict[str, str | int | float],
        fields: dict[str, int | float],
        timestamp: int | None = None,
    ):
        """
        Write a metric to VictoriaMetrics

        Arguments:
        - measurement: The name of the metric
        - tags: A dictionary of tags
        - fields: A dictionary of fields and their values
        - timestamp: Optional. The timestamp in seconds (int)

        Examples:
        metrics.write("cpu", {"host": "server1"}, {"usage": 0.5})
        metrics.write("cpu", {"host": "server1"}, {"usage": 0.5}, timestamp=1609459200)
        """
        url = url_join(self.url, "/write").rstrip("/")
        requests.post(
            url, data=self.to_line_protocol(measurement, tags, fields, timestamp)
        )

    def write_many(
        self,
        data: list[Point | dict],
    ):
        """
        Write multiple metrics to VictoriaMetrics

        Arguments:

        - data: A list of Point objects or dictionaries

        Examples:

        points = [
            Point(measurement="cpu", tags={"host": "server1"}, fields={"usage": 0.5}),
            Point(measurement="cpu", tags={"host": "server1"}, fields={"usage": 0.5}, timestamp=1609459200),
        ]

        metrics.write_many(points)

        or

        points = [
            {"measurement": "cpu", "tags": {"host": "server1"}, "fields": {"usage": 0.5}},
            {"measurement": "cpu", "tags": {"host": "server1"}, "fields": {"usage": 0.5}, "timestamp": 1609459200},
        ]

        metrics.write_many(points)

        """
        url = url_join(self.url, "/write").rstrip("/")

        lines = []

        for point in data:

            if not isinstance(point, Point):
                point = Point(**point)

            lines.append(
                self.to_line_protocol(
                    point.measurement, point.tags, point.fields, point.timestamp
                )
            )

        lines = "\n".join(lines)
        requests.post(url, data=lines, auth=self.auth)

    def query(self, query: str, keep_metric_names: bool = False) -> QueryResult:
        """
        Query a metric from Victoriametrics

        https://docs.victoriametrics.com/metricsql/

        Arguments:

        - query: The query string (PromQL/MetricsQL)
        - keep_metric_names: If True, the metric names are preserved in the result. If False, the metric names are removed from the result.

        Examples:

        ## Query all cpu_usage metrics
        metrics.query("cpu_usage")

        ## Query cpu_usage metric for host server1 (tag)
        metrics.query("cpu_usage{host='server1'}")
        """

        url = url_join(self.url, "/api/v1/query").rstrip("/")

        if keep_metric_names and "keep_metric_names" not in query:
            query = f"{query} keep_metric_names"

        data = requests.get(url, params={"query": query}, auth=self.auth).json()
        return QueryResult(**data)

    def query_range(
        self,
        query: str,
        start: str,
        step: str,
        end: str | None = None,
        timeout: str | None = None,
        keep_metric_names: bool = False,
        max_lookback: str | None = None,
    ) -> QueryResult:
        """
        Query a metric range from Victoriametrics

        https://docs.victoriametrics.com/metricsql/

        Arguments:

        - query: The query string (PromQL/MetricsQL)
        - start:  the starting timestamp of the time range for query evaluation. Can take values like "-1d" (1 day ago), "-1h" (1 hour ago), etc.
        - step: the interval between data points, which must be returned from the range query. The query is executed at start, start+step, start+2*step, …, end timestamps. If the step isn’t set, then it default to 5m (5 minutes).
        - end: the ending timestamp of the time range for query evaluation. If the end isn’t set, then the end is automatically set to the current time.
        - timeout: optional query timeout. For example, timeout=5s. Query is canceled when the timeout is reached. By default the timeout is set to the value of -search.maxQueryDuration command-line flag passed to single-node VictoriaMetrics or to vmselect component in VictoriaMetrics cluster.
        - keep_metric_names: If True, the metric names are preserved in the result. If False, the metric names are removed from the result.
        - max_lookback: optional maximum lookback duration for the query. This affects the interpolation of missing data points. A small value like `1s` will for example ensure no data points are interpolated more than 1 second away from the actual data points.
        Examples:

        ## Query all cpu_usage metrics for the last day
        metrics.query_range("cpu_usage", "-1d", "1h")

        ## Query cpu_usage metric for host server1 (tag) for the last day
        metrics.query_range("cpu_usage{host='server1'}", "-1d", "1h")
        """

        url = url_join(self.url, "/api/v1/query_range").rstrip("/")

        if keep_metric_names and "keep_metric_names" not in query:
            query = f"{query} keep_metric_names"

        params = {"query": query, "start": start, "step": step}

        if end:
            params["end"] = end

        if timeout:
            params["timeout"] = timeout

        if max_lookback:
            params["max_lookback"] = max_lookback

        data = requests.get(url, params=params, auth=self.auth).json()

        return QueryResult(**data)

    def delete(self, match: str):
        """
        Delete a metric from Victoriametrics

        Arguments:

        - match: The match string to delete the metric

        Examples:

        ## Delete all http_requests_total_count metrics

        metrics.delete('{__name__=~"http_requests_total_count"}')
        """

        url = url_join(self.url, "/api/v1/admin/tsdb/delete_series").rstrip("/")
        params = {"match[]": match}
        response = requests.get(url, params=params, auth=self.auth)
        if response.status_code != 204:
            raise Exception(
                f"Failed to delete metric: {response.status_code} {response.text}"
            )
