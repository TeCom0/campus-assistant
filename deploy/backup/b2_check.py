#!/usr/bin/env python3
"""What the VM's B2 key can do, measured, without ever printing the secret.

    b2_check.py                           the key's rights and the bucket's retention
    b2_check.py delete-test FILE_ID NAME  try to delete a version with this key

Backblaze doesn't publish what the console's access types grant, so this reads it from
b2_authorize_account. Standard library only, and only exception types in errors. Not
`b2 account get`: its output includes the auth token.
"""

import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

KEY_FILE = Path("/etc/campus-backup/b2.env")
BUCKET = "campus-assistant-backups-7"
# Exactly these, nothing more. A list of forbidden rights would have missed some: the
# console's Write Only type also grants writeBucketRetentions and
# writeBucketLifecycleRules, which would let a compromised VM weaken the bucket itself.
REQUIRED = {"writeFiles", "listBuckets", "readFileRetentions", "readBucketRetentions"}
AUTHORIZE_URL = "https://api.backblazeb2.com/b2api/v4/b2_authorize_account"


def read_key(path: Path = KEY_FILE) -> tuple[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
    return values["B2_APPLICATION_KEY_ID"], values["B2_APPLICATION_KEY"]


def authorize(key_id: str, key: str) -> dict:
    credentials = base64.b64encode(f"{key_id}:{key}".encode()).decode()
    request = urllib.request.Request(
        AUTHORIZE_URL, headers={"Authorization": f"Basic {credentials}"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def call(api_url: str, token: str, name: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{api_url}/b2api/v4/{name}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def key_problems(allowed: dict, expiry: int | None) -> list[str]:
    problems = []
    capabilities = set(allowed.get("capabilities") or [])
    missing = REQUIRED - capabilities
    if missing:
        problems.append(f"missing: {', '.join(sorted(missing))}")
    extra = capabilities - REQUIRED
    if extra:
        problems.append(f"must not have: {', '.join(sorted(extra))}")
    buckets = [bucket.get("name") for bucket in allowed.get("buckets") or []]
    if buckets != [BUCKET]:
        problems.append("not restricted to exactly this bucket")
    if allowed.get("namePrefix"):
        problems.append("has a file name prefix")
    if expiry is not None:
        problems.append("has an expiry")
    return problems


def retention_problems(lock: dict) -> list[str]:
    if not lock.get("isClientAuthorizedToRead"):
        return ["this key can't read the bucket's retention"]
    value = lock.get("value") or {}
    if not value.get("isFileLockEnabled"):
        return ["Object Lock is not enabled"]
    default = value.get("defaultRetention") or {}
    period = default.get("period") or {}
    if default.get("mode") != "compliance":
        return [f"default retention mode is {default.get('mode')}, not compliance"]
    if (period.get("duration"), period.get("unit")) != (30, "days"):
        return [f"default retention is {period.get('duration')} {period.get('unit')}, not 30 days"]
    return []


def check() -> int:
    auth = authorize(*read_key())
    api = auth["apiInfo"]["storageApi"]
    allowed = api["allowed"]
    print(f"capabilities: {', '.join(sorted(allowed.get('capabilities') or []))}")
    print(
        f"buckets:      {', '.join(str(b.get('name')) for b in allowed.get('buckets') or []) or 'all'}"
    )
    print(f"name prefix:  {allowed.get('namePrefix') or 'none'}")
    expiry = auth.get("applicationKeyExpirationTimestamp")
    print(f"expiry:       {expiry or 'none'}")
    problems = key_problems(allowed, expiry)

    # A restricted key must name its bucket in this call, or it is refused.
    if "listBuckets" in (allowed.get("capabilities") or []):
        reply = call(
            api["apiUrl"],
            auth["authorizationToken"],
            "b2_list_buckets",
            {"accountId": auth["accountId"], "bucketName": BUCKET},
        )
        lock = reply["buckets"][0].get("fileLockConfiguration") or {}
        print(f"retention:    {json.dumps(lock.get('value'))}")
        problems += retention_problems(lock)

    for problem in problems:
        print(f"PROBLEM: {problem}")
    print("KEY OK" if not problems else "KEY NOT OK")
    return 0 if not problems else 1


def delete_test(file_id: str, file_name: str) -> int:
    """The refusal is the pass. Runs only if this key really lacks deleteFiles, so
    it can't delete anything even if the lock weren't there."""
    auth = authorize(*read_key())
    api = auth["apiInfo"]["storageApi"]
    if "deleteFiles" in (api["allowed"].get("capabilities") or []):
        print("REFUSED TO TEST: this key has deleteFiles, which it must not")
        return 1
    try:
        call(
            api["apiUrl"],
            auth["authorizationToken"],
            "b2_delete_file_version",
            {"fileId": file_id, "fileName": file_name},
        )
    except urllib.error.HTTPError as e:
        code = json.load(e).get("code")
        print(f"delete refused: HTTP {e.code}, {code}")
        if e.code in (401, 403) and code in ("unauthorized", "access_denied"):
            print("DELETE REFUSED")
            return 0
        print("UNEXPECTED ERROR: not a refusal of the right")
        return 1
    print("DELETED: the key was able to delete")
    return 1


def main(argv: list[str]) -> int:
    try:
        if not argv:
            return check()
        if argv[0] == "delete-test" and len(argv) == 3:
            return delete_test(argv[1], argv[2])
        print("usage: b2_check.py [delete-test FILE_ID FILE_NAME]")
        return 2
    except Exception as e:  # noqa: BLE001 -- only its type: messages can quote a request
        print(f"CHECK FAILED: {type(e).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
