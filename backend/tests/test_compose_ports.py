"""Who can reach each published port. On a laptop only that laptop can, because the
database holds the owner's password. In production only Caddy is published."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


class _ComposeLoader(yaml.SafeLoader):
    """Compose's !reset tag ("drop the inherited value") isn't standard YAML."""


_ComposeLoader.add_constructor("!reset", lambda loader, node: None)


def _services(filename: str) -> dict:
    text = (REPO_ROOT / filename).read_text(encoding="utf-8")
    return yaml.load(text, Loader=_ComposeLoader)["services"]


def test_every_development_port_is_bound_to_this_machine_only():
    published = [
        port
        for service in _services("docker-compose.yml").values()
        for port in service.get("ports", [])
    ]
    assert len(published) == 3
    assert all(port.startswith("127.0.0.1:") for port in published)


def test_production_publishes_only_caddy():
    production = _services("docker-compose.prod.yml")
    for name in ("db", "api", "frontend"):
        assert production[name]["ports"] is None  # !reset
    assert production["caddy"]["ports"]
