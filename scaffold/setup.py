"""Test environment setup and teardown utilities."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def setup_test_environment(base_env_path: Optional[Path] = None) -> Path:
    """Set up a test environment directory.

    Always creates an isolated temporary directory for test safety.

    Args:
        base_env_path: Base environment to copy .venv from (default: ~/Desktop/Projects/test)

    Returns:
        Path to temporary test directory
    """
    base_env_path = base_env_path or Path.home() / "Desktop" / "Projects" / "test"

    for path, name in [(base_env_path, "Base environment"),
                       (base_env_path / ".venv", "Virtual environment"),
                       (base_env_path / ".venv" / "bin" / "deepagents", "deepagents")]:
        if not path.exists():
            raise FileNotFoundError(f"{name} not found at {path}")

    temp_dir = Path(tempfile.mkdtemp(prefix="deepagents_test_"))
    print(f"Setting up test environment in {temp_dir}...")
    print(f"Copying virtualenv from {base_env_path / '.venv'}...")
    shutil.copytree(base_env_path / ".venv", temp_dir / ".venv", symlinks=True)
    print("✓ Test environment ready")
    return temp_dir


def cleanup_test_environment(test_dir: Path):
    """Clean up temporary test directory."""
    # Check if it's a temp directory (starts with system temp dir or contains "deepagents_test_")
    temp_indicators = [
        tempfile.gettempdir() in str(test_dir),
        'deepagents_test_' in str(test_dir)
    ]

    if not any(temp_indicators):
        print(f"Not cleaning up {test_dir} (not a temp directory)")
        return

    if test_dir.exists():
        print(f"Cleaning up {test_dir}...")
        shutil.rmtree(test_dir)
        print("✓ Cleaned up")


def get_deepagents_python(test_dir: Path) -> Path:
    """Get path to python in test environment."""
    python = test_dir / ".venv" / "bin" / "python"
    if not python.exists():
        raise FileNotFoundError(f"Python not found at {python}")
    return python


def copy_test_data(source_file: Path, test_dir: Path):
    """Copy a test data file to the test directory."""
    if source_file.exists():
        shutil.copy2(source_file, test_dir / source_file.name)
        print(f"✓ Copied {source_file.name} to test directory")
