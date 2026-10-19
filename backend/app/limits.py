"""Protection for the public demo: a global daily question cap and a per-IP
rate limit, both counted from the question_log table in Postgres.

Postgres, not memory, so the counts survive an API restart or redeploy. The
check and the insert run in one transaction holding an advisory lock, so two
simultaneous requests can't both read "29 of 30" and both get in. Refused
questions aren't recorded, so a blocked visitor doesn't extend their own
window. IPs are stored only as a keyed hash (HMAC-SHA256), and rows older
than 2 days are deleted on each insert.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from starlette.requests import Request

from app.config import (
    DAILY_QUESTION_CAP,
    IP_HASH_SECRET,
    PER_IP_LIMIT,
    PER_IP_WINDOW_MINUTES,
    TRUST_PROXY_HEADERS,
)

# Any fixed number; it names the one lock all limit checks share.
LIMITS_LOCK_KEY = 4_242_001
RETENTION = timedelta(days=2)
_HASH_KEY = (IP_HASH_SECRET or secrets.token_hex(32)).encode()

MESSAGES = {
    "daily_cap": {
        "en": "The demo has reached its daily question limit. Please try again tomorrow.",
        "fr": "La démo a atteint sa limite quotidienne de questions. Réessayez demain.",
    },
    "per_ip": {
        "en": "You've asked several questions in a short time. Please wait a few minutes "
        "and try again.",
        "fr": "Vous avez posé plusieurs questions en peu de temps. Patientez quelques "
        "minutes, puis réessayez.",
    },
    # Groq's own per-minute limit, hit mid-answer.
    "busy": {
        "en": "The assistant is busy right now. Please try again in a minute.",
        "fr": "L'assistant est très sollicité en ce moment. Réessayez dans une minute.",
    },
}


def message(kind: str, language: str | None) -> str:
    return MESSAGES[kind]["fr" if language == "fr" else "en"]


def client_ip(request: Request, trust_proxy_headers: bool = TRUST_PROXY_HEADERS) -> str:
    """The client's IP address.

    Behind Caddy, the TCP peer is the proxy; the client is in X-Forwarded-For.
    Only the LAST entry is used, the one the proxy itself appended: earlier
    entries come from the client and could be anything.
    """
    if trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        last = forwarded.split(",")[-1].strip()
        if last:
            return last
    return request.client.host if request.client else "unknown"


def hash_ip(ip: str) -> str:
    return hmac.new(_HASH_KEY, ip.encode(), hashlib.sha256).hexdigest()


@dataclass
class Decision:
    allowed: bool
    kind: str | None = None  # "daily_cap" or "per_ip" when refused
    retry_after_seconds: int = 0


def check_and_record(
    conn,
    ip_hash: str,
    now: datetime | None = None,
    daily_cap: int = DAILY_QUESTION_CAP,
    per_ip_limit: int = PER_IP_LIMIT,
    window: timedelta = timedelta(minutes=PER_IP_WINDOW_MINUTES),
) -> Decision:
    """Admit one question (recording it) or refuse it, atomically.

    The daily cap counts questions since 00:00 UTC; the per-IP limit counts
    this IP's questions in the last `window`.
    """
    now = now or datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LIMITS_LOCK_KEY,))
        today = conn.execute(
            "SELECT count(*) FROM question_log WHERE asked_at >= %s", (day_start,)
        ).fetchone()[0]
        if today >= daily_cap:
            tomorrow = day_start + timedelta(days=1)
            return Decision(False, "daily_cap", int((tomorrow - now).total_seconds()))

        recent = conn.execute(
            "SELECT min(asked_at), count(*) FROM question_log WHERE ip_hash = %s AND asked_at > %s",
            (ip_hash, now - window),
        ).fetchone()
        if recent[1] >= per_ip_limit:
            # When the oldest one leaves the window; with a limit of 0 there may
            # be none (min() is NULL), so then a whole window from now.
            frees_up = (recent[0] or now) + window
            return Decision(False, "per_ip", max(1, int((frees_up - now).total_seconds())))

        conn.execute("DELETE FROM question_log WHERE asked_at < %s", (now - RETENTION,))
        conn.execute("INSERT INTO question_log (asked_at, ip_hash) VALUES (%s, %s)", (now, ip_hash))
    return Decision(True)
