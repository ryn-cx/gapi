import json
import logging
from pathlib import Path
from typing import Any, override

import gapi


class TestGapiClient(gapi.AbstractGapiClient):
    """Concrete implementation of AbstractGapiClient for testing."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.test_dir = test_dir
        self._files_path = test_dir / "files"

    @override
    def save_file(self, name: str, data: dict[str, Any], model_type: str) -> None:
        """Save the API response data to a file."""
        self._files_path.mkdir(parents=True, exist_ok=True)
        file_path = self._files_path / f"{name}.json"
        file_path.write_text(json.dumps(data, indent=2))

    @override
    def update_model(
        self,
        name: str,
        model_type: str,
        customizations: gapi.GapiCustomizations | None = None,
    ) -> None:
        """Update the model by regenerating it from the saved files."""
        schema_path = self.test_dir / "schema.json"
        model_path = self.test_dir / "models.py"
        generator = gapi.GAPI(class_name=name)
        generator.add_schema_from_file(schema_path)
        for file in self._files_path.glob(f"{name}.json"):
            generator.add_object_from_file(file)
        generator.write_json_schema_to_file(schema_path)
        generator.write_pydantic_model_to_file(model_path)

    @override
    def files_path(self) -> Path:
        """Return the path where files are stored."""
        return self._files_path


test_dir = Path(__file__).parent / "manual_test_files"


def test_run_test() -> None:
    schema_path = test_dir / "schema.json"
    model_path = test_dir / "models.py"
    schema_path.unlink(missing_ok=True)
    model_path.unlink(missing_ok=True)

    # Make initial model that only supports strings
    initial_data = {"value": "string"}
    client = TestGapiClient()
    client.save_file("test_model", initial_data, "response")
    client.update_model("test_model", "response")

    # PLC0415 & I001: The import needs to happen after the file is written.
    from .manual_test_files import models  # noqa: PLC0415

    # Update model to allow integers
    client = TestGapiClient()
    invalid_data = {"value": 1}
    result = client.parse_response(models.TestModel, invalid_data, "test_model")
    assert result.value == 1
    assert isinstance(result.value, int)

    models.TestModel.model_validate({"value": "string"})
    models.TestModel.model_validate({"value": 1})
