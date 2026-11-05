"""The browser protections set in deploy/Caddyfile, read from the file itself:
no database, no network, so CI checks them on every push.

The policy starts from "nothing allowed" and adds only what the built app uses.
Report-only for now: browsers log what it would block, and block nothing.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CADDYFILE = (REPO_ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
CSP_HEADER = "Content-Security-Policy-Report-Only"

EXPECTED_POLICY = {
    "default-src": ["'none'"],
    "script-src": ["'self'"],
    "style-src": ["'self'"],
    # 'self' only: the app has no data: URLs, and a remote image is what A1.1
    # removed from answers, so this stops one even if that code ever fails.
    "img-src": ["'self'"],
    "font-src": ["'self'"],
    "connect-src": ["'self'"],
    "base-uri": ["'none'"],
    "form-action": ["'none'"],
    "frame-ancestors": ["'none'"],
}


def header_value(name: str) -> str | None:
    match = re.search(rf'^\s*{re.escape(name)} "([^"]+)"\s*$', CADDYFILE, re.MULTILINE)
    return match.group(1) if match else None


def parsed_policy() -> dict[str, list[str]]:
    policy = header_value(CSP_HEADER)
    assert policy is not None, f"{CSP_HEADER} is not set in deploy/Caddyfile"
    directives = [part.split() for part in policy.split(";") if part.strip()]
    return {name: sources for name, *sources in directives}


def test_policy_allows_only_what_the_app_uses():
    assert parsed_policy() == EXPECTED_POLICY


@pytest.mark.parametrize("weakening", ["'unsafe-inline'", "'unsafe-eval'", "*", "data:", "https:"])
def test_policy_has_no_weakening_source(weakening):
    for sources in parsed_policy().values():
        assert weakening not in sources


def test_app_has_no_inline_script_for_the_policy_to_block():
    html = (REPO_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script\b[^>]*>", html)
    assert scripts, "expected the app's entry script"
    assert all("src=" in script for script in scripts)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
        ("Cross-Origin-Opener-Policy", "same-origin"),
        # Already set; pinned so the additions above can't lose them.
        ("Strict-Transport-Security", "max-age=31536000"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ],
)
def test_other_headers(name, value):
    assert header_value(name) == value
