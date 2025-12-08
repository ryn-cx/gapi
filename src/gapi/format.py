import shutil
import subprocess


def format_with_ruff(content: str) -> str:
    """Format a Python code string using ruff via uv.

    Args:
        content: The Python code as a string.

    Returns:
        The formatted Python code as a string.
    """
    if not shutil.which("uv"):
        msg = "uv was not found"
        raise FileNotFoundError(msg)

    check_result = subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", "--stdin-filename", "temp.py", "-"],  # noqa: S607
        input=content,
        text=True,
        capture_output=True,
        check=False,
    )

    format_result = subprocess.run(
        ["uv", "run", "ruff", "format", "--stdin-filename", "temp.py", "-"],  # noqa: S607
        input=check_result.stdout,
        text=True,
        capture_output=True,
        check=False,
    )

    if not format_result:
        msg = "Ruff formatting failed"
        raise RuntimeError(msg)

    return format_result.stdout
