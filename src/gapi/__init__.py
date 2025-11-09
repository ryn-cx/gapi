import contextlib
import json
import logging
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path

import datamodel_code_generator
from degenson import SchemaBuilder
from pydantic import BaseModel

INPUT_TYPE = Mapping[str, "MAIN_TYPE"] | list["MAIN_TYPE"]
MAIN_TYPE = INPUT_TYPE | datetime | date | timedelta | str | int | float | bool

logger = logging.getLogger(__name__)


class PydanticDate(BaseModel):
    date: date


class PydanticDatetime(BaseModel):
    datetime: datetime


def anonymize_file(input_file: Path) -> None:
    """Anonymize a JSON file by replacing all values with generic values.

    Args:
        input_file: The JSON file to anonymize.
    """
    input_data: INPUT_TYPE = json.loads(input_file.read_text())
    _try_to_convert_everything(input_data)
    anonymized_data = anonymize_values(input_data)
    input_file.write_text(json.dumps(anonymized_data, indent=2))


def anonymize_values(input_data: MAIN_TYPE) -> MAIN_TYPE:
    """Recursively replace all values in the input data with generic values.

    Args:
        input_data: The data structure (dict or list) to anonymize.

    Returns:
        A new anonymized copy of the data structure (does not modify the original).
    """
    type_mapping: dict[type, MAIN_TYPE] = {
        bool: True,
        int: 0,
        float: 0.0,
        str: "string",
        datetime: "2000-01-01T00:00:00Z",
        date: "2000-01-01",
        timedelta: "P1D",
    }

    if isinstance(input_data, dict):
        result: dict[str, MAIN_TYPE] = {}
        for key, value in input_data.items():
            if isinstance(value, (list, dict)):
                result[key] = anonymize_values(value)
            else:
                result[key] = type_mapping[type(value)]
        return result
    if isinstance(input_data, list):
        result_list: list[MAIN_TYPE] = []
        for value in input_data:
            if isinstance(value, (list, dict)):
                result_list.append(anonymize_values(value))
            else:
                result_list.append(type_mapping[type(value)])
        return result_list
    return type_mapping[type(input_data)]


def _try_to_convert_values(input_data: INPUT_TYPE, key: str | int, value: str) -> None:
    """Try to convert a string values to its appropriate types."""
    # Datetime must be done before date because datetimes can be parsed as dates.
    with contextlib.suppress(ValueError):
        input_data[key] = PydanticDatetime(datetime=value).datetime

    with contextlib.suppress(ValueError):
        input_data[key] = PydanticDate(date=value).date


def _try_to_convert_everything(input_data: INPUT_TYPE) -> None:
    """Recursively try to convert all values."""
    if isinstance(input_data, dict):
        items = input_data.items()
    else:
        items = enumerate(input_data)

    for key, value in items:
        if isinstance(value, str):
            _try_to_convert_values(input_data, key, value)
        elif isinstance(value, (dict, list)):
            _try_to_convert_everything(value)


def _remove_redundant_files(input_files: list[Path]) -> None:
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        temp_file = Path(fp.name)
    try:
        generate_from_files(input_files, temp_file)
        complete_model_text = temp_file.read_text()

        # Loop through all of the files while ignoring a specific file each time to make
        # sure each file is necessary to generate the schema.
        for i, _ in enumerate(input_files):
            test_files = input_files[:i] + input_files[i + 1 :]
            with tempfile.NamedTemporaryFile(delete=False) as fp:
                temp_file2 = Path(fp.name)
            try:
                generate_from_files(test_files, temp_file2)
                test_model_text = temp_file2.read_text()

                if test_model_text == complete_model_text:
                    logger.info("File %s is redundant", input_files[i].name)
                    input_files[i].unlink()
                    input_files.pop(i)
                    _remove_redundant_files(input_files)
                    return
            finally:
                temp_file2.unlink(missing_ok=True)
    finally:
        temp_file.unlink(missing_ok=True)


def generate_from_folder(
    input_folder: Path,
    output_file: Path,
    class_name: str | None = None,
    *,
    skip_conversions: bool = False,
    remove_redundant_files: bool = False,
) -> None:
    """Generate Pydantic models from all JSON files in the input folder.

    Args:
        input_folder: The folder containing JSON files.
        output_file: The file to write the generated models to.
        class_name: The name of the main class to generate. If None, use the default
        value from datamodel-code-generator.
        skip_conversions: Whether to skip trying to convert string values to their
        appropriate types. Defaults to False.
        remove_redundant_files: If a file has no effect on the generated schema remove
        it.

    """
    generate_from_files(
        list(input_folder.glob("*.json")),
        output_file,
        class_name,
        skip_conversions=skip_conversions,
        remove_redundant_files=remove_redundant_files,
    )


def generate_from_files(
    input_files: list[Path],
    output_file: Path,
    class_name: str | None = None,
    *,
    skip_conversions: bool = False,
    remove_redundant_files: bool = False,
) -> None:
    """Generate Pydantic models from a list of JSON files.

    Args:
        input_files: The list of JSON files.
        output_file: The file to write the generated models to.
        class_name: The name of the main class to generate. If None, use the default
        value from datamodel-code-generator.
        skip_conversions: Whether to skip trying to convert string values to their
        appropriate types. Defaults to False.
        remove_redundant_files: If a file has no effect on the generated schema remove
        it.

    """
    if remove_redundant_files:
        _remove_redundant_files(input_files)

    builder = SchemaBuilder()
    for file in input_files:
        parsed_json = json.loads(file.read_text())
        if not skip_conversions:
            _try_to_convert_everything(parsed_json)
        builder.add_object(parsed_json)

    _generate_from_genson(builder, output_file, class_name)


def generate_from_object(
    input_data: INPUT_TYPE,
    output_file: Path,
    class_name: str | None = None,
    *,
    skip_conversions: bool = False,
) -> None:
    """Generate Pydantic models from a Python object (dict or list).

    Args:
        input_data: The input data as a dict or list.
        output_file: The file to write the generated models to.
        class_name: The name of the main class to generate. If None, use the default
        value from datamodel-code-generator.
        replace_parent: Whether to remove the parent wrapper class. Defaults to False.
        skip_conversions: Whether to skip trying to convert string values to their
        appropriate types. Defaults to False.
    """
    if not skip_conversions:
        _try_to_convert_everything(input_data)
    builder = SchemaBuilder()
    builder.add_object(input_data)
    _generate_from_genson(builder, output_file, class_name)


def _generate_from_genson(
    input_data: SchemaBuilder,
    output_file: Path,
    class_name: str | None = None,
) -> None:
    """Generate Pydantic models from a Python object (dict or list).

    Args:
        input_data: The input data from Genson.
        output_file: The file to write the generated models to.
        class_name: The name of the main class to generate. If None, use the default
        value from datamodel-code-generator.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    datamodel_code_generator.generate(
        input_=input_data.to_json(),
        output=output_file,
        class_name=class_name,
        input_file_type=datamodel_code_generator.InputFileType.JsonSchema,
        output_model_type=datamodel_code_generator.DataModelType.PydanticV2BaseModel,
        snake_case_field=True,
        disable_timestamp=True,
        extra_fields="forbid",
        target_python_version=datamodel_code_generator.PythonVersion.PY_313,
        output_datetime_class=datamodel_code_generator.DatetimeClassType.Awaredatetime,
    )

    # datamodel-code-generator relies on a global installation of ruff which may not be
    # present, this is a backup to ensure the generated code is formatted if ruff
    # isn't available but uv is.
    if shutil.which("uv"):
        subprocess.run(
            ["uv", "run", "ruff", "check", "--fix", str(output_file)],  # noqa: S607
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        subprocess.run(
            ["uv", "run", "ruff", "format", str(output_file)],  # noqa: S607
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
