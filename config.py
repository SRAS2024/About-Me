import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")

    # Railway provides DATABASE_URL as postgresql://...; psycopg needs postgresql+psycopg://
    _raw_db = os.environ.get("DATABASE_URL", "")
    if not _raw_db:
        import warnings
        warnings.warn("DATABASE_URL is not set – database features will be unavailable")
        _raw_db = "postgresql+psycopg://postgres:postgres@localhost:5432/aboutme"
    if _raw_db.startswith("postgres://"):
        _raw_db = "postgresql+psycopg://" + _raw_db.split("://", 1)[1]
    elif _raw_db.startswith("postgresql://"):
        _raw_db = "postgresql+psycopg://" + _raw_db.split("://", 1)[1]
    elif not _raw_db.startswith("postgresql+"):
        # Unrecognised scheme — leave as-is but warn
        import warnings
        warnings.warn(f"Unexpected DATABASE_URL scheme: {_raw_db[:30]}…")
    SQLALCHEMY_DATABASE_URI = _raw_db
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,      # verify connections before use (handles Railway restarts)
        "pool_recycle": 300,         # recycle connections every 5 min
        "pool_size": 5,
        "max_overflow": 10,
    }
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "SSimonds")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "MariaEduarda")

    # Optional TinyPNG key
    TINIFY_API_KEY = os.environ.get("TINIFY_API_KEY", "").strip()

    # Supported UI locales (extend as you add translations)
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_SUPPORTED_LOCALES = ["en", "pt_BR", "pt", "es", "fr", "de", "it", "ja", "ko", "zh"]
