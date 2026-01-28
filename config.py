import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/aboutme",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "SSimonds")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "MariaEduarda")

    # Optional TinyPNG key
    TINIFY_API_KEY = os.environ.get("TINIFY_API_KEY", "").strip()

    # Supported UI locales (extend as you add translations)
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_SUPPORTED_LOCALES = ["en", "pt_BR", "pt"]
