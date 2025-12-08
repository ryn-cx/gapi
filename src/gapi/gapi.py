import json
from collections.abc import Sequence
from logging import getLogger
from pathlib import Path
from tempfile import NamedTemporaryFile

import datamodel_code_generator
from degenson import SchemaBuilder
from pydantic import BaseModel

from .constants import INPUT_TYPE
from .convert import convert_input_data
from .format import format_with_ruff

default_logger = getLogger(__name__)


class CustomField(BaseModel):
    class_name: str
    field_name: str
    new_field: str


class CustomSerializer(BaseModel):
    class_name: str | None = None
    field_name: str
    serializer_code: str


class GapiCustomizations(BaseModel):
    custom_fields: list[CustomField] = []
    custom_serializers: list[CustomSerializer] = []
    custom_imports: list[str] = []


class GAPI:
    def __init__(
        self,
        class_name: str | None = None,
        builder: SchemaBuilder | None = None,
        *,
        convert: bool = True,
    ) -> None:
        self.convert = convert
        self.builder = builder or SchemaBuilder()

        self.class_name = None
        if class_name:
            self.class_name = class_name.replace("_", " ").title().replace(" ", "")

        self.cached_json_schema: str | None = None
        self.cached_pydantic_model: str | None = None
        self.replacement_fields: list[CustomField] = []
        self.additional_serializers: list[CustomSerializer] = []
        self.additional_imports: list[str] = []

    def add_customizations(
        self,
        customizations: GapiCustomizations | None = None,
    ) -> None:
        """Add customizations to the GapiCustomizations.

        Args:
            customizations: The GapiCustomizations to add.
        """
        if not customizations:
            return

        for custom_field in customizations.custom_fields:
            self.add_replacement_field(
                class_name=custom_field.class_name,
                field_name=custom_field.field_name,
                new_field=custom_field.new_field,
            )
        for custom_serializer in customizations.custom_serializers:
            self.add_custom_serializer(
                class_name=custom_serializer.class_name,
                field_name=custom_serializer.field_name,
                serializer_code=custom_serializer.serializer_code,
            )
        for import_line in customizations.custom_imports:
            self.add_additional_import(import_line)

    def add_replacement_field(
        self,
        class_name: str,
        field_name: str,
        new_field: str,
    ) -> None:
        """Add a custom field to the GapiCustomizations.

        Args:
            class_name: The name of the class to add the custom field to.
            field_name: The name of the field to customize.
            new_field: The new field definition as a string.
        """
        indented_lines = [f"    {line}" for line in new_field.splitlines()]
        new_field = "\n".join(indented_lines)

        custom_field = CustomField(
            class_name=class_name,
            field_name=field_name,
            new_field=new_field,
        )
        self.replacement_fields.append(custom_field)

    def add_custom_serializer(
        self,
        field_name: str,
        serializer_code: str | list[str],
        class_name: str | None = None,
    ) -> None:
        """Add a custom serializer to the GapiCustomizations.

        Args:
            field_name: The name of the field to customize.
            serializer_code: The serializer method code as a string.
            class_name: The name of the class to add the custom serializer to.
                If None, applies to all classes with this field.
        """
        if isinstance(serializer_code, str):
            serializer_code = serializer_code.split("\n")

        serializer_code = f"""    @field_serializer("{field_name}")
    def serialize_{field_name}(self, value: Any, _info: Any) -> Any:
        {"\n        ".join(serializer_code)}
"""
        custom_serializer = CustomSerializer(
            class_name=class_name,
            field_name=field_name,
            serializer_code=serializer_code,
        )
        self.additional_serializers.append(custom_serializer)

    def add_additional_import(self, import_line: str) -> None:
        """Add an additional import line to the GapiCustomizations.

        Args:
            import_line: The import line as a string.
        """
        self.additional_imports.append(import_line)

    def add_schema_from_file(
        self,
        schema_path: Path,
        *,
        allow_missing: bool = True,
    ) -> None:
        """Load a JSON schema from a file path into the SchemaBuilder.

        Args:
            schema_path: Path to the JSON schema file.
            allow_missing: If True, do not raise an error if the file does not exist.
        """
        if not schema_path.exists():
            if allow_missing:
                return
            msg = f"Schema file {schema_path} does not exist."
            raise FileNotFoundError(msg)

        if not schema_path.is_file():
            msg = "schema_path must be a file."
            raise ValueError(msg)

        self.add_schema_from_string(schema_path.read_text())

    def add_schema_from_string(self, schema_string: str) -> None:
        """Load a JSON schema from a string into the SchemaBuilder.

        Args:
            schema_string: The JSON schema as a string.
        """
        self.add_schema_from_dict(json.loads(schema_string))

    def add_schema_from_dict(self, schema_dict: dict[str, INPUT_TYPE]) -> None:
        """Load a JSON schema from a dictionary into the SchemaBuilder.

        Args:
            schema_dict: The JSON schema as a dictionary.
        """
        self.cached_json_schema = None
        self.cached_pydantic_model = None

        # reportUnknownMemberType - Error is from the library.
        self.builder.add_schema(schema_dict)  # type: ignore[reportUnknownMemberType]

    def add_objects_from_folder(
        self,
        folder_path: Path,
        *,
        file_pattern: str = "*.json",
    ) -> None:
        """Load multiple JSON objects from files in a folder into the SchemaBuilder.

        Args:
            folder_path: Path to the folder containing JSON files.
            file_pattern: Glob pattern to match JSON files.
        """
        if not folder_path.is_dir():
            msg = "folder_path must be a directory."
            raise ValueError(msg)

        for json_file in folder_path.glob(file_pattern):
            self.add_object_from_file(json_file)

    def add_object_from_file(self, file_path: Path) -> None:
        """Load a single JSON object from a file into the SchemaBuilder.

        Args:
            file_path: Path to the JSON file.
        """
        if not file_path.is_file():
            msg = "file_path must be a file."
            raise ValueError(msg)

        self.add_object_from_string(file_path.read_text())

    def add_object_from_string(self, data_string: str) -> None:
        """Load a single JSON object from a string into the SchemaBuilder.

        Args:
            data_string: The JSON object as a string.
        """
        data = json.loads(data_string)
        self.add_object_from_dict(data)

    def add_object_from_dict(self, data: INPUT_TYPE) -> None:
        """Load a single JSON object from a dictionary into the SchemaBuilder.

        Args:
            data: The JSON object as a dictionary or list.
        """
        self.cached_json_schema = None
        self.cached_pydantic_model = None

        # reportUnknownMemberType - Error is from the library.
        if self.convert:
            data = convert_input_data(data)

        self.builder.add_object(data)  # type: ignore[reportUnknownMemberType]

    def get_json_schema_content(self) -> str:
        """Get the generated JSON schema as a serialized string.

        Returns:
            The JSON schema as a string.
        """
        if self.cached_json_schema is not None:
            return self.cached_json_schema
        self.cached_json_schema = self.builder.to_json()  # type: ignore[reportUnknownMemberType]
        return self.cached_json_schema

    def write_json_schema_to_file(self, output_path: Path) -> None:
        """Write the generated JSON schema to a file.

        Args:
            output_path: Path to the output JSON schema file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.get_json_schema_content())

    def get_pydantic_model_content(
        self,
    ) -> str:
        """Generate and return the Pydantic model content as a string.

        Returns:
            The generated Pydantic model content as a string.
        """
        if self.cached_pydantic_model is not None:
            return self.cached_pydantic_model

        with NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        datamodel_code_generator.generate(
            # reportUnknownMemberType - Error is from the library.
            input_=self.get_json_schema_content(),  # type: ignore[reportUnknownMemberType]
            output=temp_path,
            class_name=self.class_name,
            input_file_type=datamodel_code_generator.InputFileType.JsonSchema,
            output_model_type=datamodel_code_generator.DataModelType.PydanticV2BaseModel,
            snake_case_field=True,
            disable_timestamp=True,
            extra_fields="forbid",
            target_python_version=datamodel_code_generator.PythonVersion.PY_313,
            output_datetime_class=datamodel_code_generator.DatetimeClassType.Awaredatetime,
        )

        content = temp_path.read_text()
        temp_path.unlink()
        content = self._replace_untyped_lists(content)
        content = self._apply_additional_imports(content)
        content = self._apply_replacement_fields(content)
        content = self._apply_additional_serializers(content)
        content = format_with_ruff(content)

        self.cached_pydantic_model = content
        return content

    def write_pydantic_model_to_file(self, output_path: Path) -> None:
        """Generate and write the Pydantic model to a file.

        Args:
            output_path: Path to the output Pydantic model file.
            class_name: Optional class name for the generated model.
            customizations: Optional customizations to apply to the generated model.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.get_pydantic_model_content())

    def _get_all_class_names(self, lines: Sequence[str]) -> list[str]:
        class_names: list[str] = []
        for line in lines:
            if line.strip().startswith("class ") and "(BaseModel):" in line:
                # Extract class name from "class ClassName(BaseModel):"
                class_name = line.strip().removeprefix("class ").split("(")[0].strip()
                class_names.append(class_name)
        return class_names

    def _get_class_indexes(
        self,
        lines: Sequence[str],
        class_name: str,
    ) -> tuple[int, int]:
        class_line = f"class {class_name}(BaseModel):"
        start_index = None
        end_index = None

        for i, line in enumerate(lines):
            if class_line == line:
                start_index = i
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("class"):
                        end_index = j - 1
                        break
                else:
                    end_index = len(lines) - 1
                break

        if start_index is None or end_index is None:
            msg = f"Class '{class_name}' not found in the provided lines."
            raise ValueError(msg)

        return start_index, end_index

    def _get_field_indexes(
        self,
        lines: Sequence[str],
        class_name: str,
        field_name: str,
    ) -> tuple[int, int]:
        class_start_index, class_end_index = self._get_class_indexes(lines, class_name)
        start_index = None
        end_index = None
        for i in range(class_start_index + 1, class_end_index + 1):
            line = lines[i]
            if line.startswith(f"    {field_name}:"):
                start_index = i
                end_index = i

                if line.endswith(("(", "[")):
                    for j in range(i + 1, class_end_index + 1):
                        end_index = j
                        if lines[j].endswith((")", "]")):
                            break
                break

        if start_index is None or end_index is None:
            msg = f"Field '{field_name}' not found in the specified class."
            raise ValueError(msg)

        return start_index, end_index

    def _class_has_field(
        self,
        lines: Sequence[str],
        class_name: str,
        field_name: str,
    ) -> bool:
        start_index, end_index = self._get_class_indexes(lines, class_name)

        for i in range(start_index + 1, end_index + 1):
            if lines[i].startswith(f"    {field_name}:"):
                return True

        return False

    def _apply_additional_serializers(self, model_content: str) -> str:
        model_content = model_content.replace(
            "from pydantic import ",
            "from typing import Any\nfrom pydantic import field_serializer, ",
        )

        for serializer in self.additional_serializers:
            if serializer.class_name:
                class_line = f"class {serializer.class_name}(BaseModel):"
                replacement = class_line + "\n" + serializer.serializer_code
                model_content = model_content.replace(class_line, replacement)
            # If no class is specified add the serializer to all classes with the field.
            else:
                lines = model_content.splitlines()
                for class_name in self._get_all_class_names(lines):
                    if self._class_has_field(lines, class_name, serializer.field_name):
                        class_line = f"class {class_name}(BaseModel):"
                        replacement = class_line + "\n" + serializer.serializer_code
                        model_content = model_content.replace(class_line, replacement)

        return model_content

    def _apply_additional_imports(self, model_content: str) -> str:
        lines = model_content.splitlines()
        for i, line in enumerate(lines):
            if "#   filename:  <stdin>" in line:
                for j, import_line in enumerate(self.additional_imports):
                    lines.insert(i + 1 + j, f"{import_line}\n")

        return "\n".join(lines)

    def _apply_replacement_fields(self, model_content: str) -> str:
        for custom_field in self.replacement_fields:
            lines = model_content.splitlines()
            field_start_index, field_end_index = self._get_field_indexes(
                lines,
                custom_field.class_name,
                custom_field.field_name,
            )

            lines[field_start_index : field_end_index + 1] = [custom_field.new_field]
            model_content = "\n".join(lines)

        return model_content

    def _replace_untyped_lists(self, model_content: str) -> str:
        model_content = model_content.replace(" list ", " list[None] ")
        return model_content.replace(" list\n", " list[None]\n")
