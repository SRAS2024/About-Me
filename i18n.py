from __future__ import annotations

from flask import request
from flask_babel import Babel


babel = Babel()


def select_locale(app) -> str:
    supported = app.config.get("BABEL_SUPPORTED_LOCALES", ["en"])
    # Use best match; Flask provides Accept-Language parsing
    best = request.accept_languages.best_match(supported)
    return best or app.config.get("BABEL_DEFAULT_LOCALE", "en")
