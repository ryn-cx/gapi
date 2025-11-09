import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import ClassVar

from gapi import MAIN_TYPE, anonymize_values, generate_from_files, generate_from_object


class TestGenerateFromObject:
    def test_datetime_conversion(self) -> None:
        expected_output_file = Path("tests/datetime_conversion.output")
        expected_output = expected_output_file.read_text()
        """Test automatic datetime conversion from strings."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            output_file = Path(f.name)
        try:
            data: dict[str, str] = {"test_datetime": "2024-01-15T10:30:00Z"}
            generate_from_object(data, output_file, "TestDateTime")
            assert output_file.read_text() == expected_output
        finally:
            output_file.unlink()

    def test_date_conversion(self) -> None:
        """Test automatic date conversion from strings."""
        expected_output_file = Path("tests/date_conversion.output")
        expected_output = expected_output_file.read_text()
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            output_file = Path(f.name)
        try:
            data: dict[str, str] = {"test_date": "2024-01-15"}
            generate_from_object(data, output_file, "TestDate")
            assert output_file.read_text() == expected_output
        finally:
            output_file.unlink()

    def test_skip_conversions(self) -> None:
        """Test skipping automatic type conversions."""
        expected_output_file = Path("tests/skip_conversions.output")
        expected_output = expected_output_file.read_text()
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            output_file = Path(f.name)
        try:
            data: dict[str, str] = {
                "test_datetime": "2024-01-15T10:30:00Z",
                "test_date": "2024-01-15",
            }
            generate_from_object(data, output_file, "TestSkip", skip_conversions=True)
            assert output_file.read_text() == expected_output
        finally:
            output_file.unlink()


class TestGenerateFromFiles:
    def test_single_file(self) -> None:
        """Test generating a model from a single JSON file."""
        expected_output_file = Path("tests/single_file.output")
        expected_output = expected_output_file.read_text()
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            json_file = tmpdir / "test.json"
            json_file.write_text(json.dumps({"test_string": "String"}))

            output_file = tmpdir / "output.py"
            generate_from_files([json_file], output_file, "TestSingleFile")

            assert output_file.read_text() == expected_output

    def test_multiple_files(self) -> None:
        """Test generating a model from multiple JSON files."""
        expected_output_file = Path("tests/multiple_file.output")
        expected_output = expected_output_file.read_text()
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            file1 = tmpdir / "test1.json"
            file1.write_text(json.dumps({"test_mixed": "String"}))

            file2 = tmpdir / "test2.json"
            file2.write_text(json.dumps({"test_mixed": 123}))

            output_file = tmpdir / "output.py"
            generate_from_files([file1, file2], output_file, "Combined")

            assert output_file.read_text() == expected_output

    def test_single_redundant_file(self) -> None:
        """Test generating a model from multiple JSON files."""
        expected_output_file = Path("tests/single_redundant_file.output")
        expected_output = expected_output_file.read_text()
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            file1 = tmpdir / "test1.json"
            file1.write_text(json.dumps({"test_string": "String"}))

            file2 = tmpdir / "test2.json"
            file2.write_text(json.dumps({"test_string": "String", "test_int": 123}))

            file3 = tmpdir / "test3.json"
            file3.write_text(json.dumps({"test_int": 123}))

            output_file = tmpdir / "output.py"
            generate_from_files(
                [file1, file2, file3],
                output_file,
                "Combined",
                remove_redundant_files=True,
            )

            assert output_file.read_text() == expected_output
            number_of_remaining_files = len(list(tmpdir.glob("*.json")))
            assert number_of_remaining_files == 2  # noqa: PLR2004

    def test_multiple_redundant_files(self) -> None:
        """Test generating a model from multiple JSON files."""
        expected_output_file = Path("tests/multiple_redundant_files.output")
        expected_output = expected_output_file.read_text()
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            file1 = tmpdir / "test1.json"
            file1.write_text(json.dumps({"test_string": "String"}))

            file2 = tmpdir / "test2.json"
            file2.write_text(json.dumps({"test_string": "String"}))

            file3 = tmpdir / "test3.json"
            file3.write_text(json.dumps({"test_string": "String"}))

            output_file = tmpdir / "output.py"
            generate_from_files(
                [file1, file2, file3],
                output_file,
                "Combined",
                remove_redundant_files=True,
            )

            assert output_file.read_text() == expected_output
            number_of_remaining_files = len(list(tmpdir.glob("*.json")))
            assert number_of_remaining_files == 1

    def test_multiple_non_redundant_files(self) -> None:
        """Test generating a model from multiple JSON files."""
        expected_output_file = Path("tests/multiple_non_redundant_files.output")
        expected_output = expected_output_file.read_text()
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            file1 = tmpdir / "test1.json"
            file1.write_text(json.dumps({"test_mixed": "String"}))

            file2 = tmpdir / "test2.json"
            file2.write_text(json.dumps({"test_mixed": 123}))

            file3 = tmpdir / "test3.json"
            file3.write_text(json.dumps({"test_mixed": "2024-01-15T10:30:00Z"}))

            output_file = tmpdir / "output.py"
            generate_from_files(
                [file1, file2, file3],
                output_file,
                "Combined",
                remove_redundant_files=True,
            )

            assert output_file.read_text() == expected_output
            number_of_remaining_files = len(list(tmpdir.glob("*.json")))
            assert number_of_remaining_files == 3  # noqa: PLR2004


class TestAnonymizeValue:
    """Test anonymize_values function with all supported types."""

    def test_anonymize_bool(self) -> None:
        """Test anonymizing boolean values."""
        assert anonymize_values(input_data=True) is True
        assert anonymize_values(input_data=False) is True

    def test_anonymize_int(self) -> None:
        """Test anonymizing integer values."""
        assert anonymize_values(1) == 0
        assert anonymize_values(0) == 0

    def test_anonymize_float(self) -> None:
        """Test anonymizing float values."""
        assert anonymize_values(1.0) == 0.0
        assert anonymize_values(0.0) == 0.0

    def test_anonymize_str(self) -> None:
        """Test anonymizing string values."""
        assert anonymize_values("hello") == "string"
        assert anonymize_values("") == "string"

    def test_anonymize_datetime(self) -> None:
        """Test anonymizing datetime values."""
        test_datetime = datetime(1999, 1, 1, 0, 0, 0).astimezone()
        assert anonymize_values(test_datetime) == "2000-01-01T00:00:00Z"

    def test_anonymize_date(self) -> None:
        """Test anonymizing date values."""
        assert anonymize_values(date(1999, 1, 1)) == "2000-01-01"

    def test_anonymize_timedelta(self) -> None:
        """Test anonymizing timedelta values."""
        assert anonymize_values(timedelta(1)) == "P1D"

    TEST_LIST: ClassVar[list[MAIN_TYPE]] = [
        True,
        42,
        3.14,
        "test",
        datetime(1999, 1, 1, 0, 0, 0).astimezone(),
        date(1999, 1, 1),
        timedelta(days=1),
        {"key": "value"},
    ]

    TEST_DICT: ClassVar[dict[str, MAIN_TYPE]] = {
        "bool": False,
        "int": 42,
        "float": 3.14,
        "str": "test",
        "datetime": datetime(1999, 1, 1, 0, 0, 0).astimezone(),
        "date": date(1999, 1, 1),
        "timedelta": timedelta(days=1),
        "list": ["value 1"],
    }

    def test_anonymize_list(self) -> None:
        """Test anonymizing list values with all supported types."""
        test_input = self.TEST_LIST[:]

        # Append a duplicate copy of the list (not recursive reference)
        test_input.append(test_input[:])

        original_input = test_input[:]

        result = anonymize_values(test_input)
        assert result == [
            True,
            0,
            0.0,
            "string",
            "2000-01-01T00:00:00Z",
            "2000-01-01",
            "P1D",
            {"key": "string"},
            [
                True,
                0,
                0.0,
                "string",
                "2000-01-01T00:00:00Z",
                "2000-01-01",
                "P1D",
                {"key": "string"},
            ],
        ]

        # Make sure the original list is not modified
        assert test_input == original_input

    def test_anonymize_dict(self) -> None:
        """Test anonymizing dict values with all supported types."""
        test_input = self.TEST_DICT.copy()

        # Add a nested dict with a duplicate copy (not recursive reference)
        test_input["nested"] = test_input.copy()

        original_input = test_input.copy()

        result = anonymize_values(test_input)
        assert result == {
            "bool": True,
            "int": 0,
            "float": 0.0,
            "str": "string",
            "datetime": "2000-01-01T00:00:00Z",
            "date": "2000-01-01",
            "timedelta": "P1D",
            "list": ["string"],
            "nested": {
                "bool": True,
                "int": 0,
                "float": 0.0,
                "str": "string",
                "datetime": "2000-01-01T00:00:00Z",
                "date": "2000-01-01",
                "timedelta": "P1D",
                "list": ["string"],
            },
        }
        # Make sure the original dict is not modified
        assert test_input == original_input
