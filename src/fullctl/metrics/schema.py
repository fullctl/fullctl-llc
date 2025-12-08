import pydantic

"""
    {'status': 'success', 'data': {'resultType': 'vector', 'result': [{'metric': {'__name__': 'http_requests_total_count', 'host': 'dev6', 'service': 'devicectl'}, 'value': [1722964221, '1']}]}, 'stats': {'seriesFetched': '1', 'executionTimeMsec': 1}}
"""

__all__ = ["Stats", "Result", "Data", "QueryResult", "Point"]


class Stats(pydantic.BaseModel):
    seriesFetched: str
    executionTimeMsec: int


class Result(pydantic.BaseModel):
    metric: dict[str, str]

    # values are returned as strings to preserve precision
    # we need to convert them to float
    # vector value
    value: list[int | float] | None = None

    # matrix value
    values: list[list[int | float]] | None = None


class Data(pydantic.BaseModel):
    resultType: str
    result: list[Result] = pydantic.Field(default_factory=list)


class QueryResult(pydantic.BaseModel):
    """
    VictoriaMetrics /query response schema
    """

    status: str
    error: str | None = None
    errorType: str | None = None
    data: Data | None = None
    stats: Stats | None = None

    def __add__(self, other: "QueryResult") -> "QueryResult":

        if self.data is None:
            self.data = Data()

        if other.data is None:
            other.data = Data()

        self.data.result += other.data.result

        return self


class Point(pydantic.BaseModel):
    measurement: str
    tags: dict[str, str | int | float]
    fields: dict[str, int | float]
    timestamp: int | None = None
