import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")

    # Railway provides DATABASE_URL as postgresql://...; psycopg needs postgresql+psycopg://
    _raw_db = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/aboutme")
    if _raw_db.startswith("postgresql://"):
        _raw_db = _raw_db.replace("postgresql://", "postgresql+psycopg://", 1)
    elif _raw_db.startswith("postgres://"):
        _raw_db = _raw_db.replace("postgres://", "postgresql+psycopg://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_db
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "SSimonds")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "MariaEduarda")

    # Optional TinyPNG key
    TINIFY_API_KEY = os.environ.get("TINIFY_API_KEY", "").strip()

    # Supported UI locales (extend as you add translations)
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_SUPPORTED_LOCALES = ["en", "pt_BR", "pt", "es", "fr", "de", "it", "ja", "ko", "zh"]
