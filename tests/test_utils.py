from fullctl.utils import chunk_list


def test_chunk_list():
    test_data = range(10)
    result = [chunk for chunk in chunk_list(data=test_data, chunk_size=5)]
    assert test_data[:5] == result[0]
    assert test_data[5:] == result[1]
