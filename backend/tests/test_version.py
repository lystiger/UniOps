"""The one version the deployment is checked against.

Three files carry the version: pyproject.toml, backend/app/main.py, and
frontend/package.json. A release is tagged from the first and scripts/deploy.sh
confirms the deploy by comparing that tag to what /api/health answers, which
comes from the second. If those two drift, every deploy fails its own health
check and says only that the version was wrong.
"""

import tomllib
from pathlib import Path

from app.main import VERSION

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_the_reported_version_matches_the_packaged_one():
    packaged = tomllib.loads(PYPROJECT.read_text())["project"]["version"]
    assert VERSION == packaged
