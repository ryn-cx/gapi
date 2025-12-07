import json
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest

import gapi
from tests.constants import (
    APPENDED_TEST_DATA,
    EXPECTED_SCHEMA_PATH,
    TEST_DATA,
    TEST_SCHEMA_NO_CONVERT_PATH,
    TEST_SCHEMA_PATH,
    TEST_SCHEMA_UPDATED_NO_CONVERT_PATH,
    TEST_SCHEMA_UPDATED_PATH,
    UPDATED_EXPECTED_SCHEMA_PATH,
)


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


class TestGenerateJsonSchema:
    @staticmethod
    def validate_output(schema: gapi.GAPI, *, convert: bool) -> None:
        expected_path = TEST_SCHEMA_PATH if convert else TEST_SCHEMA_NO_CONVERT_PATH
        # reportUnknownMemberType - Error is from the library.
        output = schema.builder.to_json()  # type: ignore[reportUnknownMemberType]
        expected_output = json.loads(expected_path.read_text())
        assert json.loads(output) == expected_output

    @staticmethod
    def validate_updated_output(schema: gapi.GAPI, *, convert: bool) -> None:
        expected_path = (
            TEST_SCHEMA_UPDATED_PATH if convert else TEST_SCHEMA_UPDATED_NO_CONVERT_PATH
        )
        # reportUnknownMemberType - Error is from the library.
        output = schema.builder.to_json()  # type: ignore[reportUnknownMemberType]
        expected_output = json.loads(expected_path.read_text())
        assert json.loads(output) == expected_output

    @pytest.mark.parametrize("convert", [True, False])
    def test_generate_using_file(self, *, convert: bool) -> None:
        """Test generating JSON schema from a JSON file."""
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as file:
            json.dump(TEST_DATA, file)
            input_file = Path(file.name)
        try:
            generator = gapi.GAPI(convert=convert)
            generator.add_object_from_file(input_file)
            TestGenerateJsonSchema.validate_output(generator, convert=convert)
        finally:
            input_file.unlink()

    @pytest.mark.parametrize("convert", [True, False])
    def test_generate_using_multiple_files(self, *, convert: bool) -> None:
        """Test generating JSON schema from a JSON file."""
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as file:
            json.dump(TEST_DATA, file)
            input_file = Path(file.name)
        try:
            generator = gapi.GAPI(convert=convert)
            generator.add_object_from_file(input_file)
            generator.add_object_from_file(input_file)
            TestGenerateJsonSchema.validate_output(generator, convert=convert)
        finally:
            input_file.unlink()

    @pytest.mark.parametrize("convert", [True, False])
    def test_update_using_file(
        self,
        *,
        convert: bool,
    ) -> None:
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as file:
            json.dump(APPENDED_TEST_DATA, file)
            input_file = Path(file.name)
        try:
            generator = gapi.GAPI(convert=convert)
            existing_schema_path = (
                TEST_SCHEMA_PATH if convert else TEST_SCHEMA_NO_CONVERT_PATH
            )
            generator.add_schema_from_file(existing_schema_path)

            generator.add_object_from_file(input_file)
            TestGenerateJsonSchema.validate_updated_output(
                generator,
                convert=convert,
            )

        finally:
            input_file.unlink()

    class TestUsingFolder:
        @pytest.mark.parametrize("convert", [True, False])
        def test_generate_using_folder(self, *, convert: bool) -> None:
            """Test generating JSON schema from a folder of JSON files."""
            with TemporaryDirectory() as tmpdir_str:
                tmpdir = Path(tmpdir_str)

                for i in range(3):
                    file_path = tmpdir / f"{i}.json"
                    file_path.write_text(json.dumps(TEST_DATA))

                generator = gapi.GAPI(convert=convert)
                generator.add_objects_from_folder(tmpdir)
                TestGenerateJsonSchema.validate_output(
                    generator,
                    convert=convert,
                )

        @pytest.mark.parametrize("convert", [True, False])
        def test_update_using_folder(
            self,
            *,
            convert: bool,
        ) -> None:
            """Test updating existing schema with new data from folder."""
            with TemporaryDirectory() as tmpdir_str:
                tmpdir = Path(tmpdir_str)

                for i in range(3):
                    file_path = tmpdir / f"{i}.json"
                    file_path.write_text(json.dumps(APPENDED_TEST_DATA))

                generator = gapi.GAPI(convert=convert)

                existing_schema_path = (
                    TEST_SCHEMA_PATH if convert else TEST_SCHEMA_NO_CONVERT_PATH
                )
                generator.add_schema_from_file(existing_schema_path)

                generator.add_objects_from_folder(tmpdir)
                TestGenerateJsonSchema.validate_updated_output(
                    generator,
                    convert=convert,
                )

    class TestUsingListOfFiles:
        @pytest.mark.parametrize("convert", [True, False])
        def test_generate_using_list_of_files(self, *, convert: bool) -> None:
            """Test generating JSON schema from a list of JSON files."""
            files: list[Path] = []
            try:
                for _ in range(3):
                    with NamedTemporaryFile(
                        mode="w",
                        suffix=".json",
                        delete=False,
                    ) as file:
                        json.dump(TEST_DATA, file)
                        files.append(Path(file.name))

                generator = gapi.GAPI(convert=convert)
                for file_path in files:
                    generator.add_object_from_file(file_path)
                TestGenerateJsonSchema.validate_output(
                    generator,
                    convert=convert,
                )
            finally:
                for file in files:
                    file.unlink()

        @pytest.mark.parametrize("convert", [True, False])
        def test_update_using_list_of_files(
            self,
            *,
            convert: bool,
        ) -> None:
            """Test updating existing schema with new data from list of files."""
            files: list[Path] = []
            try:
                for _ in range(3):
                    with NamedTemporaryFile(
                        mode="w",
                        suffix=".json",
                        delete=False,
                    ) as file:
                        json.dump(APPENDED_TEST_DATA, file)
                        files.append(Path(file.name))

                generator = gapi.GAPI(convert=convert)

                existing_schema_path = (
                    TEST_SCHEMA_PATH if convert else TEST_SCHEMA_NO_CONVERT_PATH
                )
                generator.add_schema_from_file(existing_schema_path)

                for file_path in files:
                    generator.add_object_from_file(file_path)
                TestGenerateJsonSchema.validate_updated_output(
                    generator,
                    convert=convert,
                )
            finally:
                for file in files:
                    file.unlink()


class TestGeneratePydanticModel:
    def test_generate_from_schema_file(self) -> None:
        """Test generating Pydantic model from JSON schema file."""
        generator = gapi.GAPI()
        generator.add_schema_from_file(TEST_SCHEMA_PATH)
        assert (
            generator.get_pydantic_model_content() == EXPECTED_SCHEMA_PATH.read_text()
        )

    def test_generate_from_schema_dict(self) -> None:
        """Test generating Pydantic model from JSON schema dict."""
        generator = gapi.GAPI()
        generator.add_schema_from_dict(json.loads(TEST_SCHEMA_PATH.read_text()))
        assert (
            generator.get_pydantic_model_content() == EXPECTED_SCHEMA_PATH.read_text()
        )

    def test_write_to_file(self) -> None:
        """Test writing Pydantic model to file."""
        with NamedTemporaryFile(suffix=".py", delete=False) as file:
            output_file = Path(file.name)
        try:
            generator = gapi.GAPI()
            generator.add_object_from_dict(TEST_DATA)
            generator.write_pydantic_model_to_file(output_file)
            assert output_file.read_text() == EXPECTED_SCHEMA_PATH.read_text()
        finally:
            output_file.unlink()


class TestCustomFields:
    def test_apply_single_line_customization(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path("tests/test_data/custom_field_single_line.py")
        generator = gapi.GAPI()
        generator.add_object_from_dict(TEST_DATA)
        generator.add_replacement_field(
            class_name="Model",
            field_name="field_datetime",
            new_field="field_datetime: AwareDatetime",
        )
        assert (
            generator.get_pydantic_model_content()
            == specific_expected_output.read_text()
        )

    def test_apply_multiple_line_customization(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path(
            "tests/test_data/custom_field_multiple_lines.py",
        )
        test_data = deepcopy(TEST_DATA)
        test_data["FieldNameThatIsLongWithMultipleLines"] = "String"

        generator = gapi.GAPI()
        generator.add_object_from_dict(test_data)
        generator.add_replacement_field(
            class_name="Model",
            field_name="field_name_that_is_long_with_multiple_lines",
            new_field="field_name_that_is_long_with_multiple_lines: str",
        )
        assert (
            generator.get_pydantic_model_content()
            == specific_expected_output.read_text()
        )

    def test_add_string_serializer(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path(
            "tests/test_data/custom_multiple_line_serializer.py",
        )
        generator = gapi.GAPI()
        generator.add_object_from_dict(TEST_DATA)
        generator.add_custom_serializer(
            field_name="field_datetime",
            serializer_code='strf_string ="%Y-%m-%dT%H:%M:%S.%f"\n'
            "return value.strftime(strf_string)",
            class_name="Model",
        )
        assert (
            generator.get_pydantic_model_content()
            == specific_expected_output.read_text()
        )

    def test_add_list_serializer(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path(
            "tests/test_data/custom_multiple_line_serializer.py",
        )
        generator = gapi.GAPI()
        generator.add_object_from_dict(TEST_DATA)
        generator.add_custom_serializer(
            field_name="field_datetime",
            serializer_code=[
                'strf_string ="%Y-%m-%dT%H:%M:%S.%f"',
                "return value.strftime(strf_string)",
            ],
            class_name="Model",
        )
        assert (
            generator.get_pydantic_model_content()
            == specific_expected_output.read_text()
        )

    def test_add_serializer_to_all_classes(
        self,
    ) -> None:
        """Test applying GAPI customizations to a Pydantic model file."""
        specific_expected_output = Path(
            "tests/test_data/custom_multiple_line_serializer.py",
        )
        generator = gapi.GAPI()
        generator.add_object_from_dict(TEST_DATA)
        generator.add_custom_serializer(
            field_name="field_datetime",
            serializer_code='strf_string ="%Y-%m-%dT%H:%M:%S.%f"\n'
            "return value.strftime(strf_string)",
        )
        assert (
            generator.get_pydantic_model_content()
            == specific_expected_output.read_text()
        )

    def test_add_custom_import(self) -> None:
        """Test adding custom imports after the filename comment line."""
        generator = gapi.GAPI()
        generator.add_object_from_dict(TEST_DATA)
        generator.add_additional_import("from pydantic import NaiveDatetime")
        # Need to include a usage of NaiveDatetime to ensure the import is not
        # removed by ruff.
        generator.add_replacement_field(
            class_name="Model",
            field_name="field_datetime",
            new_field="field_datetime: NaiveDatetime",
        )

        content = generator.get_pydantic_model_content()

        # The custom import will be merged into the pydantic import by ruff so the
        # string to be checked does not match the input.
        assert (
            "import AwareDatetime, BaseModel, ConfigDict, Field, NaiveDatetime"
            in content
        )
