"""Password hashing — stdlib only, no external dependency.

This is deliberately narrow: the domain expert confirmed real login
(admin/manager/supervisor/dealer roles, later a mobile app, later
per-position permissions) is the actual goal, but that's a real feature
needing its own design pass (sessions, the access model, how "one editor,
all viewers" from CLAUDE.md evolves into role-based permissions). What
can't wait is: never store a password as plain text. So this module only
makes sure a password is hashed the moment it's typed — `verify_password`
exists so the format is exercised by tests now, not guessed at later, but
nothing calls it yet because there is no login screen yet.
"""

from __future__ import annotations

import hashlib
import hmac
import os

_ITERATIONS = 200_000


def hash_password(plain: str) -> str:
    """Returns "" for an empty password (meaning "no password set"),
    otherwise "<salt hex>$<hash hex>"."""
    if not plain:
        return ""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt_hex, digest_hex = stored.split("$", 1)
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    actual = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _ITERATIONS)
    return hmac.compare_digest(actual, expected)
