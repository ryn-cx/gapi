from pathlib import Path

from gapi.constants import MAIN_TYPE

TEST_DATA_FOLDER = Path("tests/test_data/")
TEST_SCHEMA_PATH = TEST_DATA_FOLDER / "test_schema.json"
TEST_SCHEMA_NO_CONVERT_PATH = TEST_DATA_FOLDER / "test_schema_no_convert.json"
TEST_SCHEMA_UPDATED_PATH = TEST_DATA_FOLDER / "test_schema_updated.json"
TEST_SCHEMA_UPDATED_NO_CONVERT_PATH = (
    TEST_DATA_FOLDER / "test_schema_updated_no_convert.json"
)
EXPECTED_SCHEMA_PATH = TEST_DATA_FOLDER / "expected_schema.py"
UPDATED_EXPECTED_SCHEMA_PATH = TEST_DATA_FOLDER / "expected_schema_updated.py"

# TODO: Test for optional data
TEST_DATA: dict[str, MAIN_TYPE] = {
    "_datetime": "2000-01-01T00:00:00Z",
    "_date": "2000-01-01",
    "_timedelta": "P3D",
    "_int": 1,
    "_float": 1.0,
    "_str": "string",
    "_bool": True,
    "_list": [
        "2000-01-01T00:00:00Z",
    ],
    "_dict": {
        "key": "string",
    },
    "FieldNameThatIsLongWithMultipleLines": "string",
    "mixed_numbers": [1, 1.0],
}

APPENDED_TEST_DATA: dict[str, MAIN_TYPE] = {
    **TEST_DATA,
    "new_field": "value",
}
