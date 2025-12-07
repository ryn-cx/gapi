from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from gapi.convert import convert_input_data, convert_value

if TYPE_CHECKING:
    from gapi.constants import INPUT_TYPE


class TestConvert:
    def test_convert_datetime(self) -> None:
        """Test converting datetime strings in dict."""
        assert isinstance(convert_value("2024-01-15T10:30:00Z"), datetime)

    def test_convert_date_string(self) -> None:
        """Test converting date strings in dict."""
        assert isinstance(convert_value("2024-01-15"), date)

    def test_convert_timedelta(self) -> None:
        """Test converting timedelta strings in dict."""
        assert isinstance(convert_value("P3D"), timedelta)

    def test_convert_no_op(self) -> None:
        """Test converting timedelta strings in dict."""
        assert isinstance(convert_value("string"), str)


class TestConvertEverything:
    @pytest.mark.parametrize(
        ("input_data", "expected_type"),
        [
            ("2000-01-01T00:00:00Z", datetime),
            ("2000-01-01", date),
            ("P1D", timedelta),
        ],
    )
    def test_convert_dict(
        self,
        *,
        input_data: str,
        expected_type: type,
    ) -> None:
        """Test converting values in dict."""
        dict_input: INPUT_TYPE = {"key_1": input_data}
        dict_input = convert_input_data(dict_input)
        assert type(dict_input) is dict
        assert type(dict_input["key_1"]) is expected_type

    @pytest.mark.parametrize(
        ("input_data", "expected_type"),
        [
            ("2000-01-01T00:00:00Z", datetime),
            ("2000-01-01", date),
            ("P1D", timedelta),
        ],
    )
    def test_convert_list(
        self,
        *,
        input_data: str,
        expected_type: type,
    ) -> None:
        """Test converting values in list."""
        list_input: INPUT_TYPE = [input_data]
        list_input = convert_input_data(list_input)
        assert type(list_input) is list
        assert type(list_input[0]) is expected_type

    @pytest.mark.parametrize(
        ("input_data", "expected_type"),
        [
            ("2000-01-01T00:00:00Z", datetime),
            ("2000-01-01", date),
            ("P1D", timedelta),
        ],
    )
    def test_convert_nested_dict(
        self,
        *,
        input_data: str,
        expected_type: type,
    ) -> None:
        """Test converting values in nested dict."""
        nested_dict_input: INPUT_TYPE = {
            "key_1": input_data,
            "key_2": {"key_3": input_data},
        }
        nested_dict_input = convert_input_data(nested_dict_input)
        assert type(nested_dict_input) is dict
        assert type(nested_dict_input["key_1"]) is expected_type
        assert type(nested_dict_input["key_2"]) is dict
        assert type(nested_dict_input["key_2"]["key_3"]) is expected_type

    @pytest.mark.parametrize(
        ("input_data", "expected_type"),
        [
            ("2000-01-01T00:00:00Z", datetime),
            ("2000-01-01", date),
            ("P1D", timedelta),
        ],
    )
    def test_convert_nested_list(
        self,
        *,
        input_data: str,
        expected_type: type,
    ) -> None:
        """Test converting values in nested list."""
        nested_list_input: INPUT_TYPE = [input_data, [input_data]]
        nested_list_input = convert_input_data(nested_list_input)
        assert type(nested_list_input) is list
        assert type(nested_list_input[0]) is expected_type
        assert type(nested_list_input[1]) is list
        assert type(nested_list_input[1][0]) is expected_type
