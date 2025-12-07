import importlib
import json
import logging
import sys
from abc import abstractmethod
from logging import getLogger
from pathlib import Path
from typing import Any, overload

from pydantic import BaseModel, ValidationError

from .gapi import GapiCustomizations

default_logger = getLogger(__name__)


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
            response_model = self.reload_model(response_model)
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
