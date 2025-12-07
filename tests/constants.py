from pathlib import Path

from gapi.constants import MAIN_TYPE

TEST_DATA_FOLDER = Path("tests/test_data/")

SCHEMA_PATH = TEST_DATA_FOLDER / "schema.json"
SCHEMA_NO_CONVERT_PATH = TEST_DATA_FOLDER / "schema_no_convert.json"
SCHEMA_UPDATED_PATH = TEST_DATA_FOLDER / "schema_updated.json"
SCHEMA_UPDATED_NO_CONVERT_PATH = TEST_DATA_FOLDER / "schema_updated_no_convert.json"

MODEL_PATH = TEST_DATA_FOLDER / "models.py"
MODEL_UPDATED_PATH = TEST_DATA_FOLDER / "models_updated.py"
MODEL_CUSTOM_FIELD_SINGLE_LINE_PATH = (
    TEST_DATA_FOLDER / "models_custom_field_single_line.py"
)
MODEL_CUSTOM_FIELD_MULTIPLE_LINES_PATH = (
    TEST_DATA_FOLDER / "models_custom_field_multiple_lines.py"
)
MODEL_CUSTOM_MULTIPLE_LINE_SERIALIZER_PATH = (
    TEST_DATA_FOLDER / "models_custom_multiple_line_serializer.py"
)

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
