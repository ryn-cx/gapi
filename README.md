# gapi
Good Ass Pydantic Integrator

A tool for generating Pydantic models from multiple JSON files with automatic date and
datetime detection.

## Features
- Combines multiple JSON files into a single output model.
- Automatically detects and converts date and datetime strings in JSON data
- Generates clean Pydantic v2 models with proper typing
- Built on top of [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator)
- Uses a forked version of [GenSON](https://github.com/wolverdude/GenSON) to create
  intermediate JSON Schemas.

## Installation

Install using [uv](https://docs.astral.sh/uv/):

```bash
uv add git+https://github.com/ryn-cx/gapi
```

## Usage

The main function `generate()` takes a folder of JSON files and generates a Pydantic model:

```python
from pathlib import Path
from gapi import generate

# Generate a model from JSON files
generate(
    input_folder=Path("json_data"),
    output_file=Path("models.py"),
    class_name="MyModel"
)
```
