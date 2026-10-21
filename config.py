import os
import secrets
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


class Config:
    # Set SECRET_KEY in Railway. Without it a random key is generated per process,
    # which is safe but logs the admin out whenever the app restarts.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Database
    # Railway commonly sets DATABASE_URL. Use it as the single source of truth.
    # Normalize scheme for SQLAlchemy + psycopg and ensure SSL when appropriate.
    _raw_db = (os.environ.get("DATABASE_URL") or "").strip()

    if not _raw_db:
        # Do not silently fall back to localhost in production. If DATABASE_URL is missing,
        # database dependent features (uploads) will fail and should be obvious.
        raise RuntimeError("DATABASE_URL is not set. Set it in Railway variables for this service.")

    def _normalize_db_url(raw: str) -> str:
        # Accept postgres://, postgresql://, or already-normalized SQLAlchemy URLs.
        if raw.startswith("postgres://"):
            raw = "postgresql://" + raw.split("://", 1)[1]

        # If already a SQLAlchemy URL like postgresql+psycopg://, keep it.
        if raw.startswith("postgresql+"):
            normalized = raw
        elif raw.startswith("postgresql://"):
            normalized = "postgresql+psycopg://" + raw.split("://", 1)[1]
        else:
            # Unknown scheme, pass through (better to error fast than guess wrong)
            return raw

        # Ensure sslmode=require when connecting to managed Postgres (common on Railway)
        # If user explicitly provided sslmode, respect it.
        try:
            parsed = urlparse(normalized)
            qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
            local_hosts = ("localhost", "127.0.0.1", "::1", "db")
            if "sslmode" not in qs and (parsed.hostname or "") not in local_hosts:
                qs["sslmode"] = "require"
                parsed = parsed._replace(query=urlencode(qs))
                normalized = urlunparse(parsed)
        except Exception:
            # If parsing fails, leave as-is.
            pass

        return normalized

    SQLALCHEMY_DATABASE_URI = _normalize_db_url(_raw_db)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection resiliency for Railway restarts
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    }

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit

    # Admin credentials come only from the environment (Railway variables).
    # If either is missing, admin login is disabled rather than falling back to a known value.
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

    # Optional TinyPNG key
    TINIFY_API_KEY = os.environ.get("TINIFY_API_KEY", "").strip()

    # Supported UI locales
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_SUPPORTED_LOCALES = ["en", "pt_BR", "pt", "es", "fr", "de", "it", "ja", "ko", "zh"]
