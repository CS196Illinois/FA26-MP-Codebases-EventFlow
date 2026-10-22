"""User accounts for EventFlow, stored in users.json as {"username": "<pbkdf2_sha256 hash>"}."""
import json
import os
from pathlib import Path

from flask_login import UserMixin
from passlib.hash import pbkdf2_sha256

# users.json lives in the repo root, next to .env (override with USERS_FILE in .env)
REPO_ROOT = Path(__file__).resolve().parent.parent
USERS_FILE = Path(os.getenv("USERS_FILE", REPO_ROOT / "users.json"))
if not USERS_FILE.is_absolute():
    USERS_FILE = REPO_ROOT / USERS_FILE


class User(UserMixin):
    def __init__(self, username):
        self.id = username


def load_users():
    """Return {username: password_hash}; empty if users.json doesn't exist yet."""
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text() or "{}")


def hash_password(password):
    return pbkdf2_sha256.hash(password)


def check_credentials(username, password):
    """Return a User if the username exists and the password matches its hash, else None."""
    password_hash = load_users().get(username)
    if password_hash and pbkdf2_sha256.verify(password, password_hash):
        return User(username)
    return None
