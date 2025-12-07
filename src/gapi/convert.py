import contextlib
import re
from copy import deepcopy
from datetime import date, datetime, timedelta
from logging import getLogger

from pydantic import TypeAdapter

from gapi.constants import INPUT_TYPE

default_logger = getLogger(__name__)


def convert_value(value: str) -> str | datetime | date | timedelta:
    """Convert a value to a more specific type if possible.

    Returns the converted value if successful, otherwise returns the original string.
    """
    # Do not trust strings that are just integers/floats because it's very easy for them
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


def _convert_all_values(input_data: INPUT_TYPE) -> None:
    """Recursively convert all values to more specific types if possible.

    This function modifies the input data in place.
    """
    # This code is intentional duplicated for type checking purposes.
    if isinstance(input_data, dict):
        for key, value in input_data.items():
            if isinstance(value, str):
                input_data[key] = convert_value(value)
            elif isinstance(value, (dict, list)):
                _convert_all_values(value)
    else:
        for key, value in enumerate(input_data):
            if isinstance(value, str):
                input_data[key] = convert_value(value)
            elif isinstance(value, (dict, list)):
                _convert_all_values(value)


def convert_input_data(input_data: INPUT_TYPE) -> INPUT_TYPE:
    """Convert all values in the input data to more specific types if possible."""
    input_data = deepcopy(input_data)
    _convert_all_values(input_data)
    return input_data
