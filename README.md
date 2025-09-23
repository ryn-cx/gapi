# gapi
**Good Ass Pydantic Integrator**

A tool for generating Pydantic models from multiple JSON files with automatic date and datetime detection.

## ✨ Features

- 📁 **Multiple File Support** - Combines multiple JSON files into a single output model
- 🕐 **Smart Date Detection** - Automatically detects and converts date and datetime strings in JSON data
- 🏗️ **Clean Model Generation** - Generates clean Pydantic v2 models with proper typing
- ⚡ **Powered by datamodel-code-generator** - Built on top of [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator)
- 🔄 **Enhanced Schema Building** - Uses a [forked version](https:/github.com/ryn-cx/DeGenSON) of [GenSON](https://github.com/wolverdude/GenSON) to create intermediate JSON Schemas

## 📦 Installation

Install using [uv](https://docs.astral.sh/uv/):

```bash
uv add git+https://github.com/ryn-cx/gapi
```

## 🚀 Quick Start

### Generate from a folder of JSON files
```python
from pathlib import Path
import gapi

gapi.generate_from_folder(
    input_folder=Path("json_data"),
    output_file=Path("models.py"),
    class_name="MyModel"
)
```

### Generate from specific files
```python
input_files = [Path("data1.json"), Path("data2.json")]
gapi.generate_from_files(
    input_files=input_files,
    output_file=Path("models.py"),
    class_name="MyModel"
)
```

### Generate from Python objects
```python
input_data = {"name": "John", "created_at": "2023-01-01T12:00:00Z"}
gapi.generate_from_object(
    input_data=input_data,
    output_file=Path("models.py"),
    class_name="Person"
)
```

## 📅 Date/DateTime Detection

The tool automatically detects and converts:

| Format | Example | Converts To |
|--------|---------|-------------|
| ISO 8601 DateTime (UTC) | `2023-01-01T12:00:00Z` | `datetime` |
| ISO 8601 DateTime (with timezone) | `2023-01-01T12:00:00+05:00` | `datetime` |
| ISO 8601 Date | `2023-01-01` | `date` |
