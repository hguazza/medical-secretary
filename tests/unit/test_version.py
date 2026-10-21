import tomllib
from pathlib import Path

import medical_secretary

ROOT = Path(__file__).resolve().parents[2]


def test_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert medical_secretary.__version__ == pyproject["project"]["version"]
