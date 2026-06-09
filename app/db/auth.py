import hashlib
import hmac
import os
import secrets

from app.db.connection import db_cursor

HASH_ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    ).hex()
    return salt, digest


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, candidate_hash = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def _default_users() -> list[dict[str, str]]:
    return [
        {
            "username": os.getenv("APP_ADMIN_USERNAME", "admin"),
            "password": os.getenv("APP_ADMIN_PASSWORD", "admin1234"),
            "display_name": os.getenv("APP_ADMIN_DISPLAY_NAME", "관리자"),
            "role": "admin",
        },
        {
            "username": os.getenv("APP_CUSTOMER_USERNAME", "customer"),
            "password": os.getenv("APP_CUSTOMER_PASSWORD", "customer1234"),
            "display_name": os.getenv("APP_CUSTOMER_DISPLAY_NAME", "테스트 고객"),
            "role": "customer",
        },
    ]


def ensure_default_users() -> None:
    with db_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS count FROM app_users")
        count = int(cursor.fetchone()["count"])
        if count > 0:
            return

        for user in _default_users():
            salt, password_hash = hash_password(user["password"])
            cursor.execute(
                """
                INSERT INTO app_users (
                    username, display_name, role, password_salt, password_hash
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user["username"],
                    user["display_name"],
                    user["role"],
                    salt,
                    password_hash,
                ),
            )


def authenticate_user(username: str, password: str) -> dict | None:
    ensure_default_users()
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, display_name, role, password_salt, password_hash
            FROM app_users
            WHERE username = ? AND is_active = TRUE
            """,
            (username,),
        )
        user = cursor.fetchone()

    if not user:
        return None
    if not verify_password(password, user["password_salt"], user["password_hash"]):
        return None

    return {
        "id": int(user["id"]),
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
    }
