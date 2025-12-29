from logging import Logger, getLogger
from pathlib import Path

from degenson import SchemaBuilder

from .gapi import GAPI

default_logger = getLogger(__name__)


def recursively_remove_redundant_files(
    root_directory: Path,
    logger: Logger = default_logger,
) -> None:
    """Remove redundant JSON files that produce the same schema.

    Args:
        root_directory: The root directory containing model subdirectories.
        logger: Logger instance to use for logging redundant files.
    """
    for model in root_directory.iterdir():
        if model.name == ".git" or model.is_file():
            continue

        json_files = list(model.glob("*.json"))
        remove_redundant_files(json_files, logger)
        recursively_remove_redundant_files(model, logger)


def remove_redundant_files(
    input_files: Path | list[Path],
    logger: Logger = default_logger,
    complete_schema: SchemaBuilder | None = None,
    starting_index: int = 0,
) -> None:
    """Remove redundant JSON files that produce the same schema.

    Args:
        input_files: Either a directory containing JSON files or a list of
            JSON file paths.
        logger: Logger instance to use for logging redundant files.
        complete_schema: The complete schema generated from all input files. If None,
            it will be generated from input_files.
        starting_index: The index to start checking for redundant files from.
    """
    if isinstance(input_files, Path):
        if not input_files.is_dir():
            msg = "input_files must be a directory or a list of JSON files."
            raise ValueError(msg)
        input_files = list(input_files.glob("*.json"))

    if complete_schema is None:
        generator = GAPI()
        for file in input_files:
            generator.add_object_from_file(file)
        complete_schema = generator.builder

    # Loop through all of the files while ignoring a specific file each time to make
    # sure each file is necessary to generate the schema.
    for i in range(starting_index, len(input_files)):
        test_files = input_files[:i] + input_files[i + 1 :]
        generator = GAPI()
        for file in test_files:
            generator.add_object_from_file(file)
        partial_schema = generator.builder
        if partial_schema == complete_schema:
            logger.info("File %s is redundant", input_files[i].name)
            input_files[i].unlink()
            input_files.pop(i)
            remove_redundant_files(input_files, logger, complete_schema, i)
            return
