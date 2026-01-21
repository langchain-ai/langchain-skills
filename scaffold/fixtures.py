"""
Helper utilities for test setup and execution.
"""

import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def setup_test_environment(
    base_env_path: Optional[Path] = None,
    use_temp: bool = True
) -> Path:
    """Set up a test environment directory.

    Args:
        base_env_path: Path to existing environment with deepagents installed.
                       If None, uses ~/Desktop/Projects/test
        use_temp: If True, creates a temporary directory and copies .venv.
                  If False, uses base_env_path directly.

    Returns:
        Path to test directory (temporary or base)
    """
    if base_env_path is None:
        base_env_path = Path.home() / "Desktop" / "Projects" / "test"

    if not base_env_path.exists():
        raise FileNotFoundError(f"Base environment not found at {base_env_path}")

    venv_path = base_env_path / ".venv"
    if not venv_path.exists():
        raise FileNotFoundError(f"Virtual environment not found at {venv_path}")

    deepagents = venv_path / "bin" / "deepagents"
    if not deepagents.exists():
        raise FileNotFoundError(f"deepagents not found at {deepagents}")

    if not use_temp:
        return base_env_path

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="deepagents_test_"))

    # Copy .venv to temp directory
    print(f"Setting up test environment in {temp_dir}...")
    print(f"Copying virtualenv from {venv_path}...")

    temp_venv = temp_dir / ".venv"
    shutil.copytree(venv_path, temp_venv, symlinks=True)

    print(f"✓ Test environment ready")

    return temp_dir


def cleanup_test_environment(test_dir: Path, keep_on_failure: bool = True):
    """Clean up temporary test directory.

    Args:
        test_dir: Path to test directory to clean up
        keep_on_failure: If True, only removes if directory is in /tmp
    """
    # Only auto-cleanup if it's in a temp directory
    if not str(test_dir).startswith('/tmp/'):
        print(f"Not cleaning up {test_dir} (not in /tmp)")
        return

    if test_dir.exists():
        print(f"Cleaning up {test_dir}...")
        shutil.rmtree(test_dir)
        print("✓ Cleaned up")


def get_deepagents_python(test_dir: Path) -> Path:
    """Get path to python in test environment.

    Args:
        test_dir: Path to test directory

    Returns:
        Path to python executable
    """
    python = test_dir / ".venv" / "bin" / "python"
    if not python.exists():
        raise FileNotFoundError(f"Python not found at {python}")
    return python


def copy_test_data(source_file: Path, test_dir: Path):
    """Copy a test data file to the test directory.

    Args:
        source_file: Path to the file to copy
        test_dir: Path to test directory
    """
    if source_file.exists():
        dest = test_dir / source_file.name
        shutil.copy2(source_file, dest)
        print(f"✓ Copied {source_file.name} to test directory")


def run_deepagents_test(
    agent_name: str,
    prompt: str,
    test_dir: Path,
    runner_path: Path,
    timeout: int = 180,
    env: dict = None
) -> tuple[int, str, str]:
    """Run a deepagents test via scaffold/runner.py.

    Args:
        agent_name: Name of the agent to test
        prompt: Prompt to send to agent
        test_dir: Test directory (with .venv)
        runner_path: Path to scaffold/runner.py
        timeout: Timeout in seconds
        env: Optional environment variables to pass (inherits current env if not provided)

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    python = get_deepagents_python(test_dir)

    # Inherit current environment and add any custom variables
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    result = subprocess.run(
        [
            str(python),
            str(runner_path),
            agent_name,
            prompt,
            "--working-dir",
            str(test_dir)
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(test_dir),
        env=process_env
    )

    return result.returncode, result.stdout, result.stderr


def extract_summary_path(stdout: str) -> Optional[Path]:
    """Extract summary.txt path from runner stdout.

    Args:
        stdout: Standard output from runner

    Returns:
        Path to summary.txt or None if not found
    """
    for line in stdout.split('\n'):
        if 'summary.txt' in line:
            # Extract path after "Review output:"
            if ':' in line:
                path_str = line.split(':', 1)[1].strip()
                return Path(path_str)
    return None


def run_autonomous_test(
    test_name: str,
    prompt: str,
    test_dir: Path,
    runner_path: Path,
    validate_func,
    timeout: int = 180
) -> int:
    """Run an autonomous test with standard flow.

    Args:
        test_name: Name of the test (e.g., "LangSmith Dataset Generation")
        prompt: Prompt to send to the agent
        test_dir: Test directory with .venv
        runner_path: Path to scaffold/runner.py
        validate_func: Function that takes (summary_content, test_dir) and returns (passed_list, failed_list)
        timeout: Timeout in seconds

    Returns:
        0 if test passed, 1 if failed
    """
    print("=" * 70)
    print(f"AUTONOMOUS TEST: {test_name}")
    print("=" * 70)
    print()

    print("PROMPT:")
    print("-" * 70)
    print(prompt)
    print("-" * 70)
    print()

    print(f"Test directory: {test_dir}")
    print()

    print("Running deepagents (this may take 60-180 seconds)...")
    print()

    try:
        returncode, stdout, stderr = run_deepagents_test(
            agent_name="langchain_agent",
            prompt=prompt,
            test_dir=test_dir,
            runner_path=runner_path,
            timeout=timeout
        )

        if stderr:
            print("STDERR:")
            print(stderr)
            print()

    except Exception as e:
        print(f"ERROR running test: {e}")
        return 1

    # Find the output directory from stdout
    summary_file = extract_summary_path(stdout)
    if not summary_file or not summary_file.exists():
        print("ERROR: Could not find summary file")
        print("STDOUT:")
        print(stdout)
        return 1

    print(f"✓ Output saved to: {summary_file}")
    print()

    # Read summary for display
    summary_content = summary_file.read_text()
    print("SESSION SUMMARY:")
    print("=" * 70)
    print(summary_content)
    print("=" * 70)
    print()

    print("VALIDATION:")
    print("-" * 70)

    # Run validations
    validations_passed, validations_failed = validate_func(summary_content, test_dir)

    # Print results
    for v in validations_passed:
        print(v)
    for v in validations_failed:
        print(v)

    print("-" * 70)
    print()

    if validations_failed:
        print("RESULT: FAILED")
        print()
        print("Failed checks:")
        for v in validations_failed:
            print(f"  {v}")
        return 1
    else:
        print("RESULT: PASSED")
        print(f"  All {len(validations_passed)} checks passed")
        return 0
