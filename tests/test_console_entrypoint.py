import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_defines_hermes_video_console_script():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    scripts = data["project"]["scripts"]
    assert scripts["hermes-video"] == "hermes_video.cli:main"


def test_console_entrypoint_target_is_importable_and_callable():
    from hermes_video.cli import main

    assert callable(main)


def test_module_entrypoint_runs_doctor(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_video.cli", "doctor", "--json"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
    )
    # doctor exits 0 (ok) or 1 (missing optional tools); both are valid runs.
    assert proc.returncode in {0, 1}
    assert '"status"' in proc.stdout
