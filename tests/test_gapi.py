import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import gapi

TEST_SCHEMA_PATH = Path("tests/test_schema.json")
TEST_SCHEMA_NO_CONVERT_PATH = Path("tests/test_schema_no_convert.json")
TEST_SCHEMA_UPDATED_PATH = Path("tests/test_schema_updated.json")
TEST_SCHEMA_UPDATED_NO_CONVERT_PATH = Path("tests/test_schema_updated_no_convert.json")
EXPECTED_SCHEMA_PATH = Path("tests/expected_schema.py")
UPDATED_EXPECTED_SCHEMA_PATH = Path("tests/updated_expected_schema.py")


TEST_DATA: gapi.INPUT_TYPE = {
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
        "key": "2000-01-01T00:00:00Z",
    },
}

APPENDED_TEST_DATA: gapi.INPUT_TYPE = {
    **TEST_DATA,
    "new_field": "value",
}


class TestConvert:
    def test_convert_datetime(self) -> None:
        """Test converting datetime strings in dict."""
        assert isinstance(gapi.convert_value("2024-01-15T10:30:00Z"), datetime)

    def test_convert_date_string(self) -> None:
        """Test converting date strings in dict."""
        assert isinstance(gapi.convert_value("2024-01-15"), date)

    def test_convert_timedelta(self) -> None:
        """Test converting timedelta strings in dict."""
        assert isinstance(gapi.convert_value("P3D"), timedelta)

    def test_convert_no_op(self) -> None:
        """Test converting timedelta strings in dict."""
        assert isinstance(gapi.convert_value("string"), str)


class TestConvertEverything:
    def test_convert_datetime_string_in_dict(self) -> None:
        """Test converting datetime strings in dict."""
        dict_input = {"key_1": "2000-01-01T00:00:00Z"}
        gapi.convert_everything(dict_input)
        assert isinstance(dict_input["key_1"], datetime)

    def test_convert_datetime_string_in_list(self) -> None:
        """Test converting datetime strings in list."""
        list_input = ["2000-01-01T00:00:00Z"]
        gapi.convert_everything(list_input)
        assert isinstance(list_input[0], datetime)

    def test_convert_datetime_nested_dict(self) -> None:
        """Test converting datetime strings in nested dict."""
        dict_input = {
            "key_1": "2000-01-01T00:00:00Z",
            "key_2": {"key_3": "2000-01-01T00:00:00Z"},
        }
        gapi.convert_everything(dict_input)
        assert isinstance(dict_input["key_1"], datetime)
        assert isinstance(dict_input["key_2"]["key_3"], datetime)

    def test_convert_datetime_nested_list(self) -> None:
        """Test converting datetime strings in nested list."""
        list_input = ["2000-01-01T00:00:00Z", ["2000-01-01T00:00:00Z"]]
        gapi.convert_everything(list_input)
        assert isinstance(list_input[0], datetime)
        assert isinstance(list_input[1][0], datetime)

    def test_convert_date_string_in_dict(self) -> None:
        """Test converting date strings in dict."""
        dict_input = {"key_1": "2000-01-01"}
        gapi.convert_everything(dict_input)
        assert isinstance(dict_input["key_1"], date)

    def test_convert_date_string_in_list(self) -> None:
        """Test converting date strings in list."""
        list_input = ["2000-01-01"]
        gapi.convert_everything(list_input)
        assert isinstance(list_input[0], date)

    def test_convert_date_nested_dict(self) -> None:
        """Test converting date strings in nested dict."""
        dict_input = {
            "key_1": "2000-01-01",
            "key_2": {"key_3": "2000-01-01"},
        }
        gapi.convert_everything(dict_input)
        assert isinstance(dict_input["key_1"], date)
        assert isinstance(dict_input["key_2"]["key_3"], date)

    def test_convert_date_nested_list(self) -> None:
        """Test converting date strings in nested list."""
        list_input = ["2000-01-01", ["2000-01-01"]]
        gapi.convert_everything(list_input)
        assert isinstance(list_input[0], date)
        assert isinstance(list_input[1][0], date)

    def test_convert_timedelta_string_in_dict(self) -> None:
        """Test converting timedelta strings in dict."""
        dict_input = {"key_1": "P1D"}
        gapi.convert_everything(dict_input)
        assert isinstance(dict_input["key_1"], timedelta)

    def test_convert_timedelta_string_in_list(self) -> None:
        """Test converting timedelta strings in list."""
        list_input = ["P1D"]
        gapi.convert_everything(list_input)
        assert isinstance(list_input[0], timedelta)

    def test_convert_timedelta_nested_dict(self) -> None:
        """Test converting timedelta strings in nested dict."""
        dict_input = {
            "key_1": "P1D",
            "key_2": {"key_3": "P1D"},
        }
        gapi.convert_everything(dict_input)
        assert isinstance(dict_input["key_1"], gapi.timedelta)
        assert isinstance(dict_input["key_2"]["key_3"], gapi.timedelta)

    def test_convert_timedelta_nested_list(self) -> None:
        """Test converting timedelta strings in nested list."""
        list_input = ["P1D", ["P1D"]]
        gapi.convert_everything(list_input)
        assert isinstance(list_input[0], gapi.timedelta)
        assert isinstance(list_input[1][0], gapi.timedelta)


class TestGenerateJsonSchema:
    def test_from_object(self) -> None:
        """Test generating JSON schema from object with conversions."""
        output = gapi.generate_json_schema(TEST_DATA)
        assert output.to_json() == TEST_SCHEMA_PATH.read_text()

    def test_from_object_no_convert(self) -> None:
        """Test generating JSON schema from object without conversions."""
        output = gapi.generate_json_schema(TEST_DATA, convert=False)
        assert output.to_json() == TEST_SCHEMA_NO_CONVERT_PATH.read_text()

    def test_from_objects(self) -> None:
        """Test generating JSON schema from multiple objects."""
        output = gapi.generate_json_schema(
            [TEST_DATA, TEST_DATA],
            multiple_inputs=True,
        )
        assert output.to_json() == TEST_SCHEMA_PATH.read_text()

    def test_from_objects_no_convert(self) -> None:
        """Test generating JSON schema from multiple objects without conversions."""
        output = gapi.generate_json_schema(
            [TEST_DATA, TEST_DATA],
            multiple_inputs=True,
            convert=False,
        )
        assert output.to_json() == TEST_SCHEMA_NO_CONVERT_PATH.read_text()

    def test_from_file(self) -> None:
        """Test generating JSON schema from a JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(TEST_DATA, f)
            input_file = Path(f.name)
        try:
            output = gapi.generate_json_schema(input_file)
            assert output.to_json() == TEST_SCHEMA_PATH.read_text()
        finally:
            input_file.unlink()

    def test_from_file_no_convert(self) -> None:
        """Test generating JSON schema from a JSON file without conversions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(TEST_DATA, f)
            input_file = Path(f.name)
        try:
            output = gapi.generate_json_schema(input_file, convert=False)
            assert output.to_json() == TEST_SCHEMA_NO_CONVERT_PATH.read_text()
        finally:
            input_file.unlink()

    def test_from_folder(self) -> None:
        """Test generating JSON schema from a folder of JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            for i in range(3):
                file_path = tmpdir / f"{i}.json"
                file_path.write_text(json.dumps(TEST_DATA))

            output = gapi.generate_json_schema(tmpdir)
            assert output.to_json() == TEST_SCHEMA_PATH.read_text()

    def test_from_list_of_files(self) -> None:
        """Test generating JSON schema from a list of JSON files."""
        files: list[Path] = []
        try:
            for _ in range(3):
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".json",
                    delete=False,
                ) as f:
                    json.dump(TEST_DATA, f)
                    files.append(Path(f.name))

            output = gapi.generate_json_schema(files)
            assert output.to_json() == TEST_SCHEMA_PATH.read_text()
        finally:
            for file in files:
                file.unlink()

    def test_from_list_of_files_no_convert(self) -> None:
        """Test generating JSON schema from a list of JSON files without conversions."""
        files: list[Path] = []
        try:
            for _ in range(3):
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".json",
                    delete=False,
                ) as f:
                    json.dump(TEST_DATA, f)
                    files.append(Path(f.name))

            output = gapi.generate_json_schema(files, convert=False)
            assert output.to_json() == TEST_SCHEMA_NO_CONVERT_PATH.read_text()
        finally:
            for file in files:
                file.unlink()

    def test_from_folder_no_convert(self) -> None:
        """Test generating JSON schema from folder without conversions."""
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            for i in range(3):
                file_path = tmpdir / f"{i}.json"
                file_path.write_text(json.dumps(TEST_DATA))

            output = gapi.generate_json_schema(tmpdir, convert=False)
            assert output.to_json() == TEST_SCHEMA_NO_CONVERT_PATH.read_text()

    def test_update_using_object(self) -> None:
        """Test updating existing schema with new object."""
        existing_schema = json.loads(TEST_SCHEMA_PATH.read_text())
        output = gapi.generate_json_schema(APPENDED_TEST_DATA, existing_schema)
        TEST_SCHEMA_UPDATED_PATH.write_text(output.to_json())
        assert output.to_json() == TEST_SCHEMA_UPDATED_PATH.read_text()

    def test_update_using_object_no_convert(self) -> None:
        """Test updating existing schema with new object without conversions."""
        existing_schema = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())
        output = gapi.generate_json_schema(
            APPENDED_TEST_DATA,
            existing_schema,
            convert=False,
        )
        assert output.to_json() == TEST_SCHEMA_UPDATED_NO_CONVERT_PATH.read_text()

    def test_update_using_file(self) -> None:
        """Test updating existing schema with new data from file."""
        existing_schema = json.loads(TEST_SCHEMA_PATH.read_text())

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(APPENDED_TEST_DATA, f)
            update_file = Path(f.name)
        try:
            output = gapi.generate_json_schema(update_file, existing_schema)
            assert output.to_json() == TEST_SCHEMA_UPDATED_PATH.read_text()
        finally:
            update_file.unlink()

    def test_update_using_file_no_convert(self) -> None:
        """Test updating schema from file without conversions."""
        existing_schema = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(APPENDED_TEST_DATA, f)
            update_file = Path(f.name)
        try:
            output = gapi.generate_json_schema(
                update_file,
                existing_schema,
                convert=False,
            )
            assert output.to_json() == TEST_SCHEMA_UPDATED_NO_CONVERT_PATH.read_text()
        finally:
            update_file.unlink()


class TestGeneratePydanticModel:
    def test_from_file(self) -> None:
        """Test generating Pydantic model from JSON schema file."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            output_file = Path(f.name)
        try:
            gapi.generate_pydantic_model(
                TEST_SCHEMA_PATH,
                output_file,
            )
            assert output_file.read_text() == EXPECTED_SCHEMA_PATH.read_text()
        finally:
            output_file.unlink()

    def test_from_schema(self) -> None:
        """Test generating Pydantic model from JSON schema dict."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            output_file = Path(f.name)
        try:
            gapi.generate_pydantic_model(
                json.loads(TEST_SCHEMA_PATH.read_text()),
                output_file,
            )
            assert output_file.read_text() == EXPECTED_SCHEMA_PATH.read_text()
        finally:
            output_file.unlink()

    def test_from_builder(self) -> None:
        """Test generating Pydantic model from SchemaBuilder."""
        builder = gapi.generate_json_schema(TEST_DATA)
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            output_file = Path(f.name)
        try:
            gapi.generate_pydantic_model(
                builder,
                output_file,
            )
            assert output_file.read_text() == EXPECTED_SCHEMA_PATH.read_text()
        finally:
            output_file.unlink()


class TestUpdateJsonSchemaAndPydanticModel:
    def test_new(self) -> None:
        """Test creating new schema and model files."""
        with tempfile.NamedTemporaryFile(suffix=".json") as schema_f:
            schema_path = Path(schema_f.name)

        with tempfile.NamedTemporaryFile(suffix=".py") as model_f:
            model_path = Path(model_f.name)
        try:
            gapi.update_json_schema_and_pydantic_model(
                TEST_DATA,
                schema_path,
                model_path,
            )

            assert schema_path.read_text() == TEST_SCHEMA_PATH.read_text()
            assert model_path.read_text() == EXPECTED_SCHEMA_PATH.read_text()
        finally:
            schema_path.unlink()
            model_path.unlink()

    def test_update(self) -> None:
        """Test updating existing schema with new data."""
        with tempfile.NamedTemporaryFile(suffix=".json") as schema_f:
            schema_path = Path(schema_f.name)
        with tempfile.NamedTemporaryFile(suffix=".py") as model_f:
            model_path = Path(model_f.name)

        schema_path.write_text(TEST_SCHEMA_PATH.read_text())
        try:
            gapi.update_json_schema_and_pydantic_model(
                APPENDED_TEST_DATA,
                schema_path,
                model_path,
            )
            assert schema_path.read_text() == TEST_SCHEMA_UPDATED_PATH.read_text()
            assert model_path.read_text() == UPDATED_EXPECTED_SCHEMA_PATH.read_text()
        finally:
            schema_path.unlink()
            model_path.unlink()


class TestRemoveRedundantFiles:
    def test_remove_redundant_files(self) -> None:
        """Test removing redundant JSON files that produce the same schema."""
        number_of_files = 3
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            for i in range(number_of_files):
                file_path = tmpdir / f"{i}.json"
                file_path.write_text(json.dumps(TEST_DATA))

            gapi.remove_redundant_files(tmpdir)

            remaining_files = list(tmpdir.glob("*.json"))
            assert len(remaining_files) == 1
