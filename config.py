import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")

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
            if "sslmode" not in qs:
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

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "SSimonds")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "MariaEduarda")

    # Optional TinyPNG key
    TINIFY_API_KEY = os.environ.get("TINIFY_API_KEY", "").strip()

    # Supported UI locales
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_SUPPORTED_LOCALES = ["en", "pt_BR", "pt", "es", "fr", "de", "it", "ja", "ko", "zh"]
