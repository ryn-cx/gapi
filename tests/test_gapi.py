import json
import tempfile
from pathlib import Path

from gapi import generate_from_files, generate_from_object


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
