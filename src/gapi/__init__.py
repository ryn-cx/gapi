import contextlib
import json
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

import datamodel_code_generator
from degenson import SchemaBuilder

INPUT_TYPE = dict[str, "MAIN_TYPE"] | list["MAIN_TYPE"]
MAIN_TYPE = INPUT_TYPE | datetime | date | str | int | float | bool


def _combine_json_files(input_files: list[Path]) -> list[MAIN_TYPE]:
    """Combine all JSON files in the input folder into a single list of dicts/lists."""
    input_contents = [file.read_bytes() for file in input_files]
    return [json.loads(content) for content in input_contents]


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


def _update_class_name(lines: list[str], class_name: str) -> None:
    if f"class {class_name}(BaseModel):" in lines:
        msg = f"Class name {class_name} already exists in the generated code."
        raise ValueError(msg)

    for i, line in enumerate(lines):
        if line == f"class {class_name}Item(BaseModel):":
            lines[i] = f"class {class_name}(BaseModel):"


def _remove_wrapper_class(lines: list[str]) -> None:
    """Remove the last class that is a wrapper around multiple files."""
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("class "):
            del lines[i:]
            break


def generate_from_folder(
    input_folder: Path,
    output_file: Path,
    class_name: str | None = None,
) -> None:
    """Generate Pydantic models from all JSON files in the input folder.

    Args:
        input_folder: The folder containing JSON files.
        output_file: The file to write the generated models to.
        class_name: The name of the main class to generate. If None, use the default
        value from datamodel-code-generator.

    """
    generate_from_files(list(input_folder.glob("*.json")), output_file, class_name)


def generate_from_files(
    input_files: list[Path],
    output_file: Path,
    class_name: str | None = None,
) -> None:
    """Generate Pydantic models from a list of JSON files.

    Args:
        input_files: The list of JSON files.
        output_file: The file to write the generated models to.
        class_name: The name of the main class to generate. If None, use the default
        value from datamodel-code-generator.

    """
    input_data = _combine_json_files(input_files)
    generate_from_object(input_data, output_file, class_name, replace_parent=True)


def generate_from_object(
    input_data: INPUT_TYPE,
    output_file: Path,
    class_name: str | None = None,
    *,
    replace_parent: bool = False,
) -> None:
    """Generate Pydantic models from a Python object (dict or list).

    Args:
        input_data: The input data as a dict or list.
        output_file: The file to write the generated models to.
        class_name: The name of the main class to generate. If None, use the default
        value from datamodel-code-generator.
        replace_parent: Whether to remove the parent wrapper class. Defaults to False.
    """
    _try_to_convert_everything(input_data)
    builder = SchemaBuilder()
    builder.add_object(input_data)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    datamodel_code_generator.generate(
        input_=input_data,
        output=output_file,
        class_name=class_name,
        input_file_type=datamodel_code_generator.InputFileType.Dict,
        output_model_type=datamodel_code_generator.DataModelType.PydanticV2BaseModel,
        snake_case_field=True,
        disable_timestamp=True,
        extra_fields="forbid",
        target_python_version=datamodel_code_generator.PythonVersion.PY_313,
        output_datetime_class=datamodel_code_generator.DatetimeClassType.Awaredatetime,
    )

    if replace_parent:
        lines = output_file.read_text().splitlines()
        _remove_wrapper_class(lines)
        _update_class_name(lines, class_name or "Model")
        output_file.write_text("\n".join(lines))

    # datamodel-code-generator relies on a global installation of ruff which may not be
    # present so it is more reliable to use uv to run ruff seperately because this is
    # garanteed to work because uv is required to install this package.
    subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", str(output_file)],  # noqa: S607
        check=False,
    )
    subprocess.run(
        ["uv", "run", "ruff", "format", str(output_file)],  # noqa: S607
        check=False,
    )
