import contextlib
import json
import logging
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path

import datamodel_code_generator
from degenson import SchemaBuilder

INPUT_TYPE = Mapping[str, "MAIN_TYPE"] | list["MAIN_TYPE"]
MAIN_TYPE = INPUT_TYPE | datetime | date | str | int | float | bool

logger = logging.getLogger(__name__)


def _try_to_convert_datetime(
    input_data: INPUT_TYPE,
    key: str | int,
    value: str,
) -> None:
    """Try to convert a string to a datetime object."""
    strptimes = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"]
    for strptime in strptimes:
        with contextlib.suppress(ValueError):
            # This doesn't need to be a timezone, and adding .astimezone() will break
            # the context manager.
            input_data[key] = datetime.strptime(value, strptime)  # noqa: DTZ007


def _try_to_convert_date(input_data: INPUT_TYPE, key: str | int, value: str) -> None:
    """Try to convert a string to a date object."""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        input_data[key] = date.fromisoformat(value)


def _try_to_convert_values(input_data: INPUT_TYPE, key: str | int, value: str) -> None:
    """Try to convert a string values to its appropriate types."""
    _try_to_convert_datetime(input_data, key, value)
    _try_to_convert_date(input_data, key, value)


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
            with tempfile.NamedTemporaryFile(delete=False) as fp2:
                temp_file2 = Path(fp2.name)
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
    if shutil.which("uv") and not shutil.which("ruff"):
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
