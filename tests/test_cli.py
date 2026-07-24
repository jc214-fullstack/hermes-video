import json
import os
import subprocess
import sys
from pathlib import Path


def test_cli_writes_manifest(tmp_path):
    out = tmp_path / "manifest.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_video.cli", "https://youtu.be/example", "--platform", "youtube", "--duration", "45", "--manifest", str(out)],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    payload = json.loads(proc.stdout)
    saved = json.loads(out.read_text())
    assert payload["platform"] == "youtube"
    assert saved["metadata"]["planned_frame_budget"] == 40
