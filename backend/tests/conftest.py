import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Each test gets its own data directory and no hosted-provider credentials."""
    monkeypatch.setenv("VERISKETCH_DATA_DIR", str(tmp_path / "data"))
    for key in ("VERISKETCH_HOSTED_PROVIDER", "GEMINI_API_KEY", "VERISKETCH_LOCAL_MODEL_PATH"):
        monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app()) as c:
        yield c


SPEC_DESCRIPTION = ("An adult male with an oval face, short dark hair, thick eyebrows, a narrow nose, "
                    "a small scar on the left cheek, and light facial hair.")


@pytest.fixture
def spec_profile():
    from app.services.trait_extractor import extract_traits
    return extract_traits(SPEC_DESCRIPTION).profile
