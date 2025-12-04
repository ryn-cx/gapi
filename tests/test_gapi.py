import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

import gapi

TEST_DATA_FOLDER = Path("tests/test_data/")
TEST_SCHEMA_PATH = TEST_DATA_FOLDER / "test_schema.json"
TEST_SCHEMA_NO_CONVERT_PATH = TEST_DATA_FOLDER / "test_schema_no_convert.json"
TEST_SCHEMA_UPDATED_PATH = TEST_DATA_FOLDER / "test_schema_updated.json"
TEST_SCHEMA_UPDATED_NO_CONVERT_PATH = (
    TEST_DATA_FOLDER / "test_schema_updated_no_convert.json"
)
EXPECTED_SCHEMA_PATH = TEST_DATA_FOLDER / "expected_schema.py"
UPDATED_EXPECTED_SCHEMA_PATH = TEST_DATA_FOLDER / "updated_expected_schema.py"


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
        "key": "string",
    },
    "FieldNameThatIsLongWithMultipleLines": "string",
    "mixed_numbers": [1, 1.0],
}

APPENDED_TEST_DATA: gapi.INPUT_TYPE = {
    **TEST_DATA,
    "new_field": "value",
}


def test_generate_all_expected_files() -> None:
    """Helper function to regenerate all expected files."""
    # Skip this test by default and only run this when explicitly needed to update
    # expected files.
    pytest.skip("Skipping regeneration of expected files.")

    schema = gapi.generate_json_schema(TEST_DATA)
    TEST_SCHEMA_PATH.write_text(schema.to_json())
    gapi.generate_pydantic_model(schema, EXPECTED_SCHEMA_PATH)

    updated_schema = gapi.generate_json_schema(APPENDED_TEST_DATA, schema)
    TEST_SCHEMA_UPDATED_PATH.write_text(updated_schema.to_json())
    gapi.generate_pydantic_model(
        updated_schema,
        UPDATED_EXPECTED_SCHEMA_PATH,
    )

    schema_no_convert = gapi.generate_json_schema(TEST_DATA, convert=False)
    TEST_SCHEMA_NO_CONVERT_PATH.write_text(schema_no_convert.to_json())
    gapi.generate_pydantic_model(
        schema_no_convert,
        TEST_SCHEMA_NO_CONVERT_PATH.with_suffix(".py"),
    )

    existing_schema = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())
    output = gapi.generate_json_schema(
        APPENDED_TEST_DATA,
        existing_schema,
        convert=False,
    )
    TEST_SCHEMA_UPDATED_NO_CONVERT_PATH.write_text(output.to_json())
    gapi.generate_pydantic_model(
        output,
        TEST_SCHEMA_UPDATED_NO_CONVERT_PATH.with_suffix(".py"),
    )


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
    def convert(self, input_data: str, expected_type: type) -> None:
        """Helper function to test convert_everything."""
        dict_input = {"key_1": input_data}
        gapi.convert_everything(dict_input)
        assert type(dict_input["key_1"]) is expected_type

        list_input = [input_data]
        gapi.convert_everything(list_input)
        assert type(list_input[0]) is expected_type

        nested_dict_input = {
            "key_1": input_data,
            "key_2": {"key_3": input_data},
        }
        gapi.convert_everything(nested_dict_input)
        assert type(nested_dict_input["key_1"]) is expected_type
        assert type(nested_dict_input["key_2"]["key_3"]) is expected_type

        nested_list_input = [input_data, [input_data]]
        gapi.convert_everything(nested_list_input)
        assert type(nested_list_input[0]) is expected_type
        assert type(nested_list_input[1][0]) is expected_type

    def test_convert_datetime(self) -> None:
        """Test converting datetime strings in dict."""
        self.convert("2000-01-01T00:00:00Z", datetime)

    def test_convert_date(self) -> None:
        """Test converting date strings in dict."""
        self.convert("2000-01-01", date)

    def test_convert_timedelta(self) -> None:
        """Test converting timedelta strings in dict."""
        self.convert("P1D", timedelta)


class TestGenerateJsonSchema:
    def test_from_object(self) -> None:
        """Test generating JSON schema from object with conversions."""
        output = gapi.generate_json_schema(TEST_DATA)
        expected = json.loads(TEST_SCHEMA_PATH.read_text())
        assert json.loads(output.to_json()) == expected

    def test_from_object_no_convert(self) -> None:
        """Test generating JSON schema from object without conversions."""
        output = gapi.generate_json_schema(TEST_DATA, convert=False)
        expected = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())
        assert json.loads(output.to_json()) == expected

    def test_from_objects(self) -> None:
        """Test generating JSON schema from multiple objects."""
        output = gapi.generate_json_schema(
            [TEST_DATA, TEST_DATA],
            multiple_inputs=True,
        )
        expected = json.loads(TEST_SCHEMA_PATH.read_text())
        assert json.loads(output.to_json()) == expected

    def test_from_objects_no_convert(self) -> None:
        """Test generating JSON schema from multiple objects without conversions."""
        output = gapi.generate_json_schema(
            [TEST_DATA, TEST_DATA],
            multiple_inputs=True,
            convert=False,
        )
        expected = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())
        assert json.loads(output.to_json()) == expected

    def test_from_file(self) -> None:
        """Test generating JSON schema from a JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(TEST_DATA, f)
            input_file = Path(f.name)
        try:
            output = gapi.generate_json_schema(input_file)
            expected = json.loads(TEST_SCHEMA_PATH.read_text())
            assert json.loads(output.to_json()) == expected
        finally:
            input_file.unlink()

    def test_from_file_no_convert(self) -> None:
        """Test generating JSON schema from a JSON file without conversions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(TEST_DATA, f)
            input_file = Path(f.name)
        try:
            output = gapi.generate_json_schema(input_file, convert=False)
            expected = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())
            assert json.loads(output.to_json()) == expected
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
            expected = json.loads(TEST_SCHEMA_PATH.read_text())
            assert json.loads(output.to_json()) == expected

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
            expected = json.loads(TEST_SCHEMA_PATH.read_text())
            assert json.loads(output.to_json()) == expected
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
            expected = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())
            assert json.loads(output.to_json()) == expected
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
            expected = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())
            assert json.loads(output.to_json()) == expected

    def test_update_using_object(self) -> None:
        """Test updating existing schema with new object."""
        existing_schema = json.loads(TEST_SCHEMA_PATH.read_text())
        output = gapi.generate_json_schema(APPENDED_TEST_DATA, existing_schema)
        expected = json.loads(TEST_SCHEMA_UPDATED_PATH.read_text())
        assert json.loads(output.to_json()) == expected

    def test_update_using_object_no_convert(self) -> None:
        """Test updating existing schema with new object without conversions."""
        existing_schema = json.loads(TEST_SCHEMA_NO_CONVERT_PATH.read_text())
        output = gapi.generate_json_schema(
            APPENDED_TEST_DATA,
            existing_schema,
            convert=False,
        )
        expected = json.loads(TEST_SCHEMA_UPDATED_NO_CONVERT_PATH.read_text())
        assert json.loads(output.to_json()) == expected

    def test_update_using_file(self) -> None:
        """Test updating existing schema with new data from file."""
        existing_schema = json.loads(TEST_SCHEMA_PATH.read_text())

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(APPENDED_TEST_DATA, f)
            update_file = Path(f.name)
        try:
            output = gapi.generate_json_schema(update_file, existing_schema)
            expected = json.loads(TEST_SCHEMA_UPDATED_PATH.read_text())
            assert json.loads(output.to_json()) == expected
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
            expected = json.loads(TEST_SCHEMA_UPDATED_NO_CONVERT_PATH.read_text())
            assert json.loads(output.to_json()) == expected
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

            expected_schema = json.loads(TEST_SCHEMA_PATH.read_text())
            assert json.loads(schema_path.read_text()) == expected_schema
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
            expected_schema = json.loads(TEST_SCHEMA_UPDATED_PATH.read_text())
            assert json.loads(schema_path.read_text()) == expected_schema
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


class TestCustomFields:
    def test_apply_single_line_customization(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path("tests/test_data/custom_field_single_line.py")
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            temp_model_path = Path(f.name)
            temp_model_path.write_text(EXPECTED_SCHEMA_PATH.read_text())

        customizations = gapi.GapiCustomizations(
            custom_fields=[
                gapi.CustomField(
                    class_name="Model",
                    field_name="field_datetime",
                    new_field="field_datetime: AwareDatetime",
                ),
            ],
        )

        try:
            gapi.apply_customizations(
                temp_model_path,
                customizations,
            )
            assert temp_model_path.read_text() == specific_expected_output.read_text()
        finally:
            temp_model_path.unlink()

    def test_apply_multiple_line_customization(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path(
            "tests/test_data/custom_field_multiple_lines.py",
        )
        test_data = TEST_DATA.copy()
        test_data["FieldNameThatIsLongWithMultipleLines"] = "String"

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_schema_path = Path(f.name)
        temp_schema_path.unlink()

        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            temp_model_path = Path(f.name)
        temp_model_path.unlink()
        gapi.update_json_schema_and_pydantic_model(
            test_data,
            temp_schema_path,
            temp_model_path,
        )
        customizations = gapi.GapiCustomizations(
            custom_fields=[
                gapi.CustomField(
                    class_name="Model",
                    field_name="field_name_that_is_long_with_multiple_lines",
                    new_field="field_name_that_is_long_with_multiple_lines: str",
                ),
            ],
        )

        try:
            gapi.apply_customizations(
                temp_model_path,
                customizations,
            )
            assert temp_model_path.read_text() == specific_expected_output.read_text()
        finally:
            temp_schema_path.unlink()
            temp_model_path.unlink()

    def test_add_multiple_line_serializer_without_space(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path(
            "tests/test_data/custom_multiple_line_serializer.py",
        )
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            temp_model_path = Path(f.name)
            temp_model_path.write_text(EXPECTED_SCHEMA_PATH.read_text())

        customizations = gapi.GapiCustomizations(
            custom_serializers=[
                gapi.CustomSerializer(
                    class_name="Model",
                    field_name="field_datetime",
                    serializer_code='strf_string ="%Y-%m-%dT%H:%M:%S.%f"\n'
                    "return value.strftime(strf_string)",
                ),
            ],
        )

        try:
            gapi.apply_customizations(
                temp_model_path,
                customizations,
            )
            assert temp_model_path.read_text() == specific_expected_output.read_text()
        finally:
            temp_model_path.unlink()

    def test_add_list_serializer_without_space(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path(
            "tests/test_data/custom_multiple_line_serializer.py",
        )
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            temp_model_path = Path(f.name)
            temp_model_path.write_text(EXPECTED_SCHEMA_PATH.read_text())

        customizations = gapi.GapiCustomizations(
            custom_serializers=[
                gapi.CustomSerializer(
                    class_name="Model",
                    field_name="field_datetime",
                    serializer_code=[
                        'strf_string ="%Y-%m-%dT%H:%M:%S.%f"',
                        "return value.strftime(strf_string)",
                    ],
                ),
            ],
        )

        try:
            gapi.apply_customizations(temp_model_path, customizations)
            assert temp_model_path.read_text() == specific_expected_output.read_text()
        finally:
            temp_model_path.unlink()

    def test_add_serializer_to_all_classes(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path(
            "tests/test_data/custom_multiple_line_serializer.py",
        )
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            temp_model_path = Path(f.name)
            temp_model_path.write_text(EXPECTED_SCHEMA_PATH.read_text())

        customizations = gapi.GapiCustomizations(
            custom_serializers=[
                gapi.CustomSerializer(
                    field_name="field_datetime",
                    serializer_code=[
                        'strf_string ="%Y-%m-%dT%H:%M:%S.%f"',
                        "return value.strftime(strf_string)",
                    ],
                ),
            ],
        )

        try:
            gapi.apply_customizations(temp_model_path, customizations)
            assert temp_model_path.read_text() == specific_expected_output.read_text()
        finally:
            temp_model_path.unlink()

    def test_add_custom_imports(self) -> None:
        """Test adding custom imports after the filename comment line."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            temp_model_path = Path(f.name)
            temp_model_path.write_text(EXPECTED_SCHEMA_PATH.read_text())

        customizations = gapi.GapiCustomizations(
            custom_imports=[
                "from pydantic import NaiveDatetime",
            ],
            # Need to include a usage of NaiveDatetime to ensure the import is not
            # removed by ruff.
            custom_fields=[
                gapi.CustomField(
                    class_name="Model",
                    field_name="field_datetime",
                    new_field="field_datetime: NaiveDatetime",
                ),
            ],
        )

        try:
            gapi.apply_customizations(temp_model_path, customizations)
            content = temp_model_path.read_text()

            # The custom import will be merged into the pydantic import by ruff so the
            # string to be checked does not match the input.
            assert (
                "import AwareDatetime, BaseModel, ConfigDict, Field, NaiveDatetime"
                in content
            )

        finally:
            temp_model_path.unlink()
