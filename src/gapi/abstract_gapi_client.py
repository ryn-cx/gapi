import importlib
import json
import logging
import sys
import uuid
from abc import abstractmethod
from logging import getLogger
from pathlib import Path
from typing import Any, overload

from pydantic import BaseModel, ValidationError

from .gapi import GAPI, GapiCustomizations

default_logger = getLogger(__name__)


class AbstractGapiClient:
    logger: logging.Logger = default_logger

    @abstractmethod
    def client_path(self) -> Path: ...

    def update_model(
        self,
        name: str,
        new_file_path: Path,
        customizations: GapiCustomizations | None = None,
    ) -> None:
        schema_path = self.schema_path(name)
        model_path = self.models_path(name)

        client = GAPI(name.replace("/", "_"))
        client.add_schema_from_file(schema_path)
        client.add_object_from_file(new_file_path)
        client.add_customizations(customizations)
        client.write_json_schema_to_file(schema_path)
        client.write_pydantic_model_to_file(model_path)

    def save_file(
        self,
        name: str,
        data: dict[str, Any],
    ) -> Path:
        """Add a new test file for a given endpoint."""
        input_folder = self.files_path() / name

        new_json_path = input_folder / f"{uuid.uuid4()}.json"
        new_json_path.parent.mkdir(parents=True, exist_ok=True)
        new_json_path.write_text(json.dumps(data, indent=2))
        return new_json_path

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

    def files_path(self) -> Path:
        return self.client_path() / "_files"

    def schema_path(self, name: str) -> Path:
        return self.client_path() / f"{name}/schema.json"

    def models_path(self, name: str) -> Path:
        return self.client_path() / f"{name}/models.py"

    def rebuild_model(
        self,
        name: str,
        customizations: GapiCustomizations | None = None,
    ) -> None:
        schema_path = self.schema_path(name)
        model_path = self.models_path(name)

        client = GAPI(name.replace("/", "_"))
        client.add_objects_from_folder(self.files_path() / name)
        client.add_customizations(customizations)
        client.write_json_schema_to_file(schema_path)
        client.write_pydantic_model_to_file(model_path)

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
            new_file_path = self.save_file(name, data)
            self.update_model(name, new_file_path, customizations)
            response_model = self.reload_model(response_model)
            parsed = response_model.model_validate(data)
            if getattr(self, "logger", None):
                self.logger.info("Updated model %s.", response_model.__name__)

        if self.dump_response(parsed) != data:
            self.save_file(name, data)
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

    def reload_model[T: BaseModel](self, model_class: type[T]) -> type[T]:
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
