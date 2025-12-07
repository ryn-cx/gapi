import json
from pathlib import Path
from tempfile import TemporaryDirectory

import gapi
from tests.constants import (
    TEST_DATA,
)


class TestRemoveRedundantFiles:
    def test_remove_redundant_files(self) -> None:
        number_of_files = 3
        with TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            for i in range(number_of_files):
                file_path = tmpdir / f"{i}.json"
                file_path.write_text(json.dumps(TEST_DATA))

            gapi.remove_redundant_files(tmpdir)

            remaining_files = list(tmpdir.glob("*.json"))
            assert len(remaining_files) == 1
