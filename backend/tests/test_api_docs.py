"""FastAPI's docs routes exist only when asked for. Anything else stays closed,
including a setting that is missing or misspelled, so a server fails closed."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
DOCS_ROUTES = ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"]


def _enabled_with(env_value: str) -> str:
    # A new process, because the setting is read once, at import.
    done = subprocess.run(
        [sys.executable, "-c", "from app.config import API_DOCS_ENABLED as e; print(e)"],
        env={**os.environ, "ENV": env_value},
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


@pytest.mark.parametrize("value", ["", "production", "Development", "dev", "development "])
def test_anything_but_the_exact_value_keeps_the_docs_off(value):
    assert _enabled_with(value) == "False"


def test_the_exact_value_turns_them_on():
    assert _enabled_with("development") == "True"


@pytest.mark.skipif(os.environ.get("ENV") == "development", reason="this shell turned them on")
@pytest.mark.parametrize("route", DOCS_ROUTES)
def test_the_app_serves_no_docs_route_by_default(route):
    assert TestClient(main.app).get(route).status_code == 404


def test_the_rest_of_the_api_still_answers():
    assert TestClient(main.app).get("/health").status_code == 200


def test_production_compose_doesnt_turn_them_on():
    for name in ("docker-compose.yml", "docker-compose.prod.yml"):
        assert "ENV:" not in (REPO_ROOT / name).read_text(encoding="utf-8").replace("_ENV:", "")
    # The VM's own .env isn't in the repo: the deploy check is a 404 on the live site.
