import contextlib
import copy
import importlib
import json
import logging
import re
import shutil
import subprocess
import sys
from abc import abstractmethod
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from logging import Logger, getLogger
from pathlib import Path
from typing import Any, overload

import datamodel_code_generator
from degenson import SchemaBuilder
from pydantic import BaseModel, TypeAdapter, ValidationError

INPUT_TYPE = dict[str, "MAIN_TYPE"] | list["MAIN_TYPE"]
MAIN_TYPE = INPUT_TYPE | datetime | date | timedelta | str | int | float | bool

default_logger = getLogger(__name__)


def convert_value(value: str) -> str | datetime | date | timedelta:
    """Convert a value to a more specific type if possible.

    Returns the converted value if successful, otherwise returns the original string.
    """
    # Do not trust strings that are just integers/flaots because it's very easy for them
    # to be cast to the wrong type.
    with contextlib.suppress(ValueError):
        int(value)
        return value

    with contextlib.suppress(ValueError):
        float(value)
        return value

    # datetime and date basically overlap so extra checks need to be done. The easiest
    # way to do this is to only validate dates of the string matches a date format and
    # assume everything else is a datetime becasue datetime is more complex than dates.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}$", value):
        with contextlib.suppress(ValueError):
            return TypeAdapter(date).validate_python(value)

    with contextlib.suppress(ValueError):
        return TypeAdapter(datetime).validate_python(value)

    with contextlib.suppress(ValueError):
        return TypeAdapter(timedelta).validate_python(value)

    return value


def convert_everything(input_data: INPUT_TYPE) -> None:
    """Recursively convert all values to more specific types if possible."""
    # This code is intentional duplicated for type checking purposes.
    if isinstance(input_data, dict):
        for key, value in input_data.items():
            if isinstance(value, str):
                input_data[key] = convert_value(value)
            elif isinstance(value, (dict, list)):
                convert_everything(value)
    else:
        for key, value in enumerate(input_data):
            if isinstance(value, str):
                input_data[key] = convert_value(value)
            elif isinstance(value, (dict, list)):
                convert_everything(value)


def _load_original_schema(
    original_schema: str | Path | dict[str, INPUT_TYPE] | None,
    builder: SchemaBuilder,
) -> None:
    if original_schema:
        if isinstance(original_schema, Path):
            if not original_schema.is_file():
                msg = "original_schema must be a file."
                raise ValueError(msg)

            original_schema = original_schema.read_text()

        if isinstance(original_schema, str):
            original_schema = json.loads(original_schema)

        builder.add_schema(original_schema)


def _parse_list_of_files(file_list: list[Path]) -> INPUT_TYPE:
    """Parse a list of JSON file paths into data objects."""
    parsed_data: list[MAIN_TYPE] = []
    for path in file_list:
        if not path.is_file():
            msg = "All paths in list must be JSON files, not directories."
            raise ValueError(msg)
        if path.suffix != ".json":
            msg = "All paths in list must be JSON files."
            raise ValueError(msg)
        parsed_data.append(json.loads(path.read_text()))
    return parsed_data


def _parse_schema_input(
    schema_input: Path | list[Path] | INPUT_TYPE,
    *,
    multiple_inputs: bool | None,
) -> tuple[INPUT_TYPE, bool | None]:
    if isinstance(schema_input, list) and all(
        isinstance(path, Path) for path in schema_input
    ):
        if multiple_inputs is None:
            multiple_inputs = True
        # reportArgumentType - The type is correct because of the if condition above.
        parsed_data = _parse_list_of_files(schema_input)  # type: ignore[reportArgumentType]
        return parsed_data, multiple_inputs

    if isinstance(schema_input, Path):
        if schema_input.is_file():
            if multiple_inputs is None:
                multiple_inputs = False
            parsed_data = json.loads(schema_input.read_text())
            return parsed_data, multiple_inputs

        if schema_input.is_dir():
            if multiple_inputs is None:
                multiple_inputs = True
            parsed_data = [
                json.loads(json_file.read_text())
                for json_file in schema_input.glob("*.json")
            ]
            return parsed_data, multiple_inputs

        msg = f"Input path {schema_input} is neither a file nor a directory."
        raise OSError(msg)

    return schema_input, multiple_inputs


def generate_json_schema(
    schema_input: Path | list[Path] | INPUT_TYPE,
    original_schema: str | Path | dict[str, INPUT_TYPE] | None = None,
    *,
    multiple_inputs: bool | None = None,
    convert: bool = True,
) -> SchemaBuilder:
    """Generate a JSON schema from a single input, which can be a file or an object.

    Args:
        schema_input: Can be a Path to a JSON file/directory, a list of Path objects
            to JSON files, or a dict/list containing input data.
        original_schema: An optional original schema to use as a base.
        multiple_inputs: Whether the input_data contains multiple inputs. If None,
            this will be inferred from the type of input_data.
        convert: Whether to attempt to convert string values to more specific types.
    """
    builder = SchemaBuilder()

    _load_original_schema(original_schema, builder)

    schema_input, multiple_inputs = _parse_schema_input(
        schema_input,
        multiple_inputs=multiple_inputs,
    )

    schema_input = copy.deepcopy(schema_input)
    if multiple_inputs:
        for schema_entry in schema_input:
            if convert:
                convert_everything(schema_entry)
            builder.add_object(schema_entry)
    else:
        if convert:
            convert_everything(schema_input)
        builder.add_object(schema_input)

    return builder


def _format_with_ruff(file_path: Path) -> None:
    """Format a Python file using ruff via uv.

    Args:
        file_path: Path to the Python file to format.
    """
    if not shutil.which("uv"):
        return

    subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", str(file_path)],  # noqa: S607
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    subprocess.run(
        ["uv", "run", "ruff", "format", str(file_path)],  # noqa: S607
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def generate_pydantic_model(
    schema_input: Path | INPUT_TYPE | SchemaBuilder,
    output_file: Path,
    class_name: str | None = None,
) -> None:
    """Generate Pydantic models from a JSON schema.

    Args:
        schema_input: Can be a Path to a JSON schema file, a dict/list containing
            schema data, or a SchemaBuilder object.
        output_file: The file to write the generated models to.
        class_name: The name of the main class to generate. If None, use the default
            value from datamodel-code-generator.
    """
    if isinstance(schema_input, SchemaBuilder):
        builder = schema_input
    else:
        builder = SchemaBuilder()
        if isinstance(schema_input, Path):
            schema_input = json.loads(schema_input.read_text())
        builder.add_schema(schema_input)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    datamodel_code_generator.generate(
        input_=builder.to_json(),
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
    _format_with_ruff(output_file)
    _replace_untyped_lists(output_file)


def update_json_schema_and_pydantic_model(
    data: INPUT_TYPE | list[Path] | Path,
    schema_path: Path,
    model_path: Path,
    name: str | None = None,
) -> None:
    """Update JSON schema and Pydantic model for given data.

    Args:
        name: The name of the schema/model. Will be converted to PascalCase for
            the class name (e.g., "user_profile" becomes "UserProfile").
        data: The input data to generate the schema from. Can be a dict or list.
        schema_path: The path where the JSON schema file will be written. If this
            file exists, it will be used as the base schema and merged with the
            new data.
        model_path: The path where the generated Pydantic model file will be
            written.
    """
    class_name = None
    if name:
        class_name = name.replace("_", " ").title().replace(" ", "")

    if schema_path.exists():
        schema = generate_json_schema(data, schema_path)
    else:
        schema = generate_json_schema(data)
    schema_path.write_text(schema.to_json())
    generate_pydantic_model(schema, model_path, class_name)


def _replace_untyped_lists(model_path: Path) -> None:
    """Replace untyped lists in a Pydantic model file with list[None].

    Args:
        model_path: Path to the Pydantic model file.
    """
    model_content = model_path.read_text()
    model_content = model_content.replace(" list ", " list[None] ")
    model_content = model_content.replace(" list\n", " list[None]\n")
    model_path.write_text(model_content)


def remove_redundant_files(
    input_files: Path | list[Path],
    logger: Logger = default_logger,
    complete_schema: SchemaBuilder | None = None,
    starting_index: int = 0,
) -> None:
    """Remove redundant JSON files that produce the same schema.

    Args:
        input_files: Either a directory containing JSON files or a list of
            JSON file paths.
        logger: Logger instance to use for logging redundant files.
        complete_schema: The complete schema generated from all input files. If None,
            it will be generated from input_files.
        starting_index: The index to start checking for redundant files from.
    """
    if isinstance(input_files, Path):
        if not input_files.is_dir():
            msg = "input_files must be a directory or a list of JSON files."
            raise ValueError(msg)
        input_files = list(input_files.glob("*.json"))

    complete_schema = complete_schema or generate_json_schema(input_files)

    # Loop through all of the files while ignoring a specific file each time to make
    # sure each file is necessary to generate the schema.
    for i in range(starting_index, len(input_files)):
        test_files = input_files[:i] + input_files[i + 1 :]
        partial_schema = generate_json_schema(test_files)
        if partial_schema == complete_schema:
            logger.info("File %s is redundant", input_files[i].name)
            input_files[i].unlink()
            input_files.pop(i)
            remove_redundant_files(input_files, logger, complete_schema, i)
            return


class CustomField(BaseModel):
    class_name: str
    field_name: str
    new_field: str


class CustomSerializer(BaseModel):
    class_name: str | None = None
    field_name: str
    serializer_code: list[str] | str


class GapiCustomizations(BaseModel):
    custom_fields: list[CustomField] = []
    custom_serializers: list[CustomSerializer] = []


def _apply_field_customizations(
    model_content: str,
    gapi_customizations: GapiCustomizations,
) -> str:
    for custom_field in gapi_customizations.custom_fields:
        class_line = f"class {custom_field.class_name}(BaseModel):"

        inside_of_class = False
        lines = model_content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(class_line):
                inside_of_class = True
            elif inside_of_class and line.startswith("class "):
                msg = (
                    f"Field {custom_field.field_name} not found"
                    "in class {custom_field.class_name}."
                )
                raise ValueError(msg)
            if inside_of_class and line.startswith(f"    {custom_field.field_name}:"):
                lines_to_replace = [line]
                j = i
                if line.rstrip().endswith(("(", "[")):
                    while not lines[j].endswith((")", "]")):
                        lines_to_replace.append(lines[j + 1])
                        j += 1

                field_definition = f"    {custom_field.new_field}"
                model_content = model_content.replace(
                    "\n".join(lines_to_replace),
                    field_definition,
                )
                break
        else:
            msg = f"Class {custom_field.class_name} not found in model."
            raise ValueError(msg)

    return model_content


def _class_has_field(
    lines: Sequence[str],
    class_index: int,
    field_name: str,
) -> bool:
    i = class_index + 1
    while i < len(lines):
        # Stop if we hit another class definition
        if lines[i].strip().startswith("class "):
            return False
        # Check if this line contains the field
        if lines[i].strip().startswith(f"{field_name}:"):
            return True
        i += 1
    return False


def _apply_serializer_customizations(
    model_content: str,
    gapi_customizations: GapiCustomizations,
) -> str:
    lines = model_content.splitlines(keepends=True)
    model_content = model_content.replace(
        "from pydantic import ",
        "from typing import Any\nfrom pydantic import field_serializer, ",
    )

    for serializer in gapi_customizations.custom_serializers:
        # Convert serializer_code to list if it's a string
        if isinstance(serializer.serializer_code, str):
            code_lines = serializer.serializer_code.split("\n")
        else:
            code_lines = serializer.serializer_code

        serializer_method = f"""    @field_serializer("{serializer.field_name}")
    def serialize_{serializer.field_name}(self, value: Any, _info: Any) -> Any:
        {"\n        ".join(code_lines)}
"""

        if serializer.class_name:
            class_line = f"class {serializer.class_name}(BaseModel):"
            for i, line in enumerate(lines):
                if f"class {serializer.class_name}(BaseModel):" in line:
                    if not _class_has_field(lines, i, serializer.field_name):
                        msg = (
                            f"Field {serializer.field_name} not found"
                            "in class {serializer.class_name}."
                        )
                        raise ValueError(msg)
                    replacement_string = class_line + "\n" + serializer_method
                    model_content = model_content.replace(
                        class_line,
                        replacement_string,
                    )
                    break
            else:
                msg = f"Class {serializer.class_name} not found in model."
                raise ValueError(msg)
        else:
            # Apply to all classes that have the field
            lines_to_replace = []

            for i, line in enumerate(lines):
                # Check if this is a class definition
                is_class = line.strip().startswith("class ")
                if is_class and _class_has_field(lines, i, serializer.field_name):
                    lines_to_replace.append(line)

            for line in lines_to_replace:
                replacement_string = line + "\n" + serializer_method
                model_content = model_content.replace(line, replacement_string)

    return model_content


def apply_customizations(
    model_path: Path,
    gapi_customizations: GapiCustomizations | None = None,
) -> None:
    """Apply customizations to a Pydantic model file.

    Args:
        model_path: Path to the Pydantic model file.
        gapi_customizations: The customizations to apply.
    """
    if not gapi_customizations:
        return

    model_content = model_path.read_text()
    model_content = _apply_field_customizations(model_content, gapi_customizations)
    model_content = _apply_serializer_customizations(model_content, gapi_customizations)
    model_path.write_text(model_content)
    _format_with_ruff(model_path)


def reload_model[T: BaseModel](model_class: type[T]) -> type[T]:
    """Dynamically reload a model class by reloading its module.

    Returns:
        The reloaded class from the reloaded module
    """
    module = sys.modules[model_class.__module__]

    if hasattr(module, "__cached__") and module.__cached__:
        cached_path = Path(module.__cached__)
        if cached_path.exists():
            cached_path.unlink()

    reloaded_module = importlib.reload(module)
    return getattr(reloaded_module, model_class.__name__)


class AbstractGapiClient:
    logger: logging.Logger = default_logger

    @overload
    def dump_response(
        self,
        data: list[list[BaseModel]],
    ) -> list[list[dict[str, Any]]]: ...
    @overload
    def dump_response(self, data: list[BaseModel]) -> list[dict[str, Any]]: ...
    @overload
    def dump_response(self, data: BaseModel) -> dict[str, Any]: ...
    def dump_response(
        self,
        data: BaseModel | list[BaseModel] | list[list[BaseModel]],
    ) -> dict[str, Any] | list[dict[str, Any]] | list[list[dict[str, Any]]]:
        """Dump an API response to a JSON serializable object."""
        if isinstance(data, list):
            return [self.dump_response(item) for item in data]

        return data.model_dump(mode="json", by_alias=True, exclude_unset=True)

    @abstractmethod
    def save_file(self, name: str, data: dict[str, Any], model_type: str) -> None: ...

    @abstractmethod
    def update_model(
        self,
        name: str,
        model_type: str,
        customizations: GapiCustomizations | None = None,
    ) -> None: ...

    @abstractmethod
    def files_path(self) -> Path: ...

    def parse_response[T: BaseModel](
        self,
        response_model: type[T],
        data: dict[str, Any],
        name: str,
        customizations: GapiCustomizations | None = None,
    ) -> T:
        try:
            parsed = response_model.model_validate(data)
        except ValidationError:
            self.save_file(name, data, "response")
            self.update_model(name, "response", customizations)
            response_model = reload_model(response_model)
            parsed = response_model.model_validate(data)
            if getattr(self, "logger", None):
                self.logger.info("Updated model %s.", response_model.__name__)

        if self.dump_response(parsed) != data:
            self.save_file(name, data, "response")
            temp_path = self.files_path() / "_temp"
            named_temp_path = temp_path / name
            named_temp_path.mkdir(parents=True, exist_ok=True)
            original_path = named_temp_path / "original.json"
            parsed_path = named_temp_path / "parsed.json"
            original_path.write_text(json.dumps(data, indent=2))
            parsed_path.write_text(json.dumps(self.dump_response(parsed), indent=2))
            msg = "Parsed response does not match original response."
            raise ValueError(msg)

        return parsed
