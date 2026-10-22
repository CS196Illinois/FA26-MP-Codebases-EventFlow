"""Create or update an EventFlow login.

Usage (from the repo root):  python Project/add_user.py USERNAME

Prompts for a password, hashes it with pbkdf2_sha256 and saves it under USERNAME
in users.json (repo root, next to .env). users.json is gitignored: never commit it.
"""
import getpass
import json
import sys

from auth import USERS_FILE, hash_password, load_users


def main():
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print("Usage: python Project/add_user.py USERNAME")
        sys.exit(1)
    username = sys.argv[1].strip()

    password = getpass.getpass(f"Password for {username}: ")
    if not password:
        print("Password can't be empty.")
        sys.exit(1)
    if getpass.getpass("Confirm password: ") != password:
        print("Passwords don't match.")
        sys.exit(1)

    users = load_users()
    action = "Updated" if username in users else "Added"
    users[username] = hash_password(password)
    USERS_FILE.write_text(json.dumps(users, indent=2) + "\n")
    print(f"{action} user '{username}' in {USERS_FILE}")


if __name__ == "__main__":
    main()
