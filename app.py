from __future__ import annotations

import logging
import os
import re
import traceback
from functools import wraps
from io import BytesIO
from typing import Any, Dict, List

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_babel import gettext as _

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from config import Config
from i18n import babel, select_locale
from models import db, Accomplishment, LinkItem, ResumeFile, SitePhoto, Trait
from services.image_processing import compress_image

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    babel.init_app(app, locale_selector=lambda: select_locale(app))

    # Reasonable defaults for session cookies behind a proxy (Railway)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)

    # Single source of truth for limits used by the backend
    MAX_TRAITS = 12

    def is_logged_in() -> bool:
        return session.get("admin_authed") is True

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not is_logged_in():
                return redirect(url_for("admin_login", next=request.path))
            return fn(*args, **kwargs)

        return wrapper

    def normalize_locale(loc: str) -> str:
        loc = (loc or "").strip()
        if not loc:
            return app.config.get("BABEL_DEFAULT_LOCALE", "en")
        if not re.fullmatch(r"[A-Za-z]{2}([_-][A-Za-z]{2,4})?", loc):
            return app.config.get("BABEL_DEFAULT_LOCALE", "en")
        return loc.replace("-", "_")

    def best_resume_locale() -> str:
        available = [r.locale for r in ResumeFile.query.all()]
        if not available:
            return app.config.get("BABEL_DEFAULT_LOCALE", "en")
        best = request.accept_languages.best_match(available)
        if best:
            return best
        accept = [lang for lang, _q in request.accept_languages]
        for lang in accept:
            base = lang.split("-")[0].split("_")[0]
            for a in available:
                if a.split("_")[0] == base:
                    return a
        return available[0]

    def get_links(kind: str) -> List[Dict[str, Any]]:
        items = (
            LinkItem.query.filter_by(kind=kind)
            .order_by(LinkItem.sort_order.asc(), LinkItem.created_at.asc())
            .all()
        )
        return [
            {
                "id": i.id,
                "kind": i.kind,
                "label": i.label,
                "url": i.url,
                "sort_order": i.sort_order,
                "pair_index": i.pair_index,
            }
            for i in items
        ]

    def get_accomplishments() -> List[Dict[str, Any]]:
        items = Accomplishment.query.order_by(
            Accomplishment.sort_order.asc(), Accomplishment.created_at.asc()
        ).all()
        return [{"id": a.id, "text": a.text, "sort_order": a.sort_order} for a in items]

    def get_traits() -> List[str]:
        items = Trait.query.order_by(Trait.sort_order.asc(), Trait.created_at.asc()).all()
        return [t.text for t in items]

    def db_ping() -> tuple[bool, str]:
        """
        Returns (ok, message). Message is safe to show in UI.
        """
        try:
            db.session.execute(text("SELECT 1"))
            return True, "ok"
        except OperationalError as exc:
            db.session.rollback()
            return False, f"database connection failed: {exc.__class__.__name__}"
        except SQLAlchemyError as exc:
            db.session.rollback()
            return False, f"database error: {exc.__class__.__name__}"
        except Exception as exc:
            db.session.rollback()
            return False, f"unexpected database error: {exc.__class__.__name__}"

    def require_db_or_503():
        ok, msg = db_ping()
        if ok:
            return None
        app.logger.error("Database not available: %s", msg)
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Database is not available",
                    "detail": msg,
                    "hint": "Verify DATABASE_URL is set for this Railway service and points to the attached Postgres.",
                }
            ),
            503,
        )

    # ── Startup logging ────────────────────────────────────────────
    port = os.environ.get("PORT", "8000")
    db_configured = bool(os.environ.get("DATABASE_URL"))
    app.logger.info("Starting app on port %s | DATABASE_URL configured: %s", port, db_configured)

    # Create tables at startup inside the app context.
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created or verified successfully")
            ok, msg = db_ping()
            if ok:
                logger.info("Database ping ok at startup")
            else:
                logger.error("Database ping failed at startup: %s", msg)
        except Exception as exc:
            logger.error(
                "Could not create database tables at startup: %s\n%s",
                exc,
                traceback.format_exc(),
            )

    # ── Health check ─────────────────────────────────────────────

    @app.get("/health")
    def health():
        ok, msg = db_ping()
        return jsonify({"status": "ok", "db_ok": ok, "db": msg}), 200

    # ── Public Routes ─────────────────────────────────────────────

    @app.get("/")
    def index():
        locale = select_locale(app)
        try:
            photo_exists = SitePhoto.query.first() is not None
            resume_locale = best_resume_locale()
            has_resume = ResumeFile.query.filter_by(locale=resume_locale).first() is not None
            github_links = get_links("github")
            website_links = get_links("website")
            accomplishments = get_accomplishments()
            traits = get_traits()
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Database unavailable on /: %s\n%s", exc, traceback.format_exc())
            return render_template(
                "index.html",
                locale=locale,
                photo_exists=False,
                resume_locale="en",
                has_resume=False,
                github_links=[],
                website_links=[],
                accomplishments=[],
                traits=[],
            )

        return render_template(
            "index.html",
            locale=locale,
            photo_exists=photo_exists,
            resume_locale=resume_locale,
            has_resume=has_resume,
            github_links=github_links,
            website_links=website_links,
            accomplishments=accomplishments,
            traits=traits,
        )

    @app.get("/assets/photo")
    def asset_photo():
        photo = SitePhoto.query.order_by(SitePhoto.created_at.desc()).first()
        if not photo:
            abort(404)
        return send_file(BytesIO(photo.bytes), mimetype=photo.mimetype, download_name=photo.filename)

    @app.get("/assets/resume")
    def asset_resume():
        requested = normalize_locale(request.args.get("locale", ""))
        resume = ResumeFile.query.filter_by(locale=requested).first()
        if not resume:
            best = best_resume_locale()
            resume = ResumeFile.query.filter_by(locale=best).first()
        if not resume:
            abort(404)
        return send_file(BytesIO(resume.bytes), mimetype=resume.mimetype, download_name=resume.filename)

    # ── Admin Routes ──────────────────────────────────────────────

    @app.get("/admin")
    @login_required
    def admin():
        locale = select_locale(app)
        try:
            photo_exists = SitePhoto.query.first() is not None
            resume_locale = best_resume_locale()
            has_resume = ResumeFile.query.filter_by(locale=resume_locale).first() is not None
            github_links = get_links("github")
            website_links = get_links("website")
            accomplishments = get_accomplishments()
            traits = get_traits()
            resumes = ResumeFile.query.order_by(ResumeFile.locale.asc()).all()
            resumes_list = [{"locale": r.locale, "filename": r.filename} for r in resumes]
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Database unavailable on /admin: %s\n%s", exc, traceback.format_exc())
            photo_exists = False
            resume_locale = "en"
            has_resume = False
            github_links = []
            website_links = []
            accomplishments = []
            traits = []
            resumes_list = []

        return render_template(
            "admin.html",
            locale=locale,
            photo_exists=photo_exists,
            resume_locale=resume_locale,
            has_resume=has_resume,
            github_links=github_links,
            website_links=website_links,
            accomplishments=accomplishments,
            traits=traits,
            resumes=resumes_list,
            supported_locales=app.config.get("BABEL_SUPPORTED_LOCALES", ["en"]),
        )

    @app.get("/admin/login")
    def admin_login():
        if is_logged_in():
            return redirect(url_for("admin"))
        return render_template("admin_login.html", next=request.args.get("next", "/admin"))

    @app.post("/admin/login")
    def admin_login_post():
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        if username == app.config["ADMIN_USERNAME"] and password == app.config["ADMIN_PASSWORD"]:
            session["admin_authed"] = True
            return redirect(request.form.get("next") or url_for("admin"))
        return render_template(
            "admin_login.html",
            next=request.form.get("next", "/admin"),
            error=_("Invalid login."),
        )

    @app.post("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("index"))

    # ── Admin APIs ────────────────────────────────────────────────

    @app.get("/admin/api/state")
    @login_required
    def admin_state():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err
        try:
            photo_exists = SitePhoto.query.first() is not None
            resumes = ResumeFile.query.order_by(ResumeFile.locale.asc()).all()
            return jsonify(
                {
                    "photo_exists": photo_exists,
                    "resumes": [{"locale": r.locale, "filename": r.filename} for r in resumes],
                    "github_links": get_links("github"),
                    "website_links": get_links("website"),
                    "accomplishments": get_accomplishments(),
                    "traits": get_traits(),
                }
            )
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Database error on /admin/api/state: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Failed to load admin state",
                        "detail": f"{exc.__class__.__name__}: {str(exc)[:200]}",
                    }
                ),
                500,
            )

    @app.put("/admin/api/traits")
    @login_required
    def admin_save_traits():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err

        data = request.get_json(force=True, silent=False) or {}
        items = data.get("traits", [])

        if not isinstance(items, list) or len(items) > MAX_TRAITS:
            return jsonify({"ok": False, "error": f"Invalid traits list (max {MAX_TRAITS})"}), 400

        cleaned: List[str] = []
        for t in items:
            if not isinstance(t, str):
                return jsonify({"ok": False, "error": "Traits must be strings"}), 400
            val = t.strip()
            if not val:
                continue
            if len(val) > 60:
                return jsonify({"ok": False, "error": "Trait too long (max 60 chars)"}), 400
            cleaned.append(val)

        try:
            Trait.query.delete()
            for idx, val in enumerate(cleaned):
                db.session.add(Trait(text=val, sort_order=idx))
            db.session.commit()
            return jsonify({"ok": True})
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Traits save failed: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Save failed",
                        "detail": f"{exc.__class__.__name__}: {str(exc)[:200]}",
                    }
                ),
                500,
            )

    @app.post("/admin/api/photo")
    @login_required
    def admin_upload_photo():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err

        if "photo" not in request.files:
            return jsonify({"ok": False, "error": "Missing file field: photo"}), 400

        f = request.files["photo"]
        raw = f.read()
        if not raw:
            return jsonify({"ok": False, "error": "Empty file"}), 400

        try:
            out_bytes, mimetype = compress_image(raw, tinify_api_key=app.config.get("TINIFY_API_KEY", ""))
            SitePhoto.query.delete()
            db.session.add(
                SitePhoto(
                    filename=(f.filename or "profile.jpg"),
                    mimetype=mimetype,
                    bytes=out_bytes,
                )
            )
            db.session.commit()
            return jsonify({"ok": True})
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Photo upload failed: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Photo upload failed",
                        "detail": f"{exc.__class__.__name__}: {str(exc)[:200]}",
                    }
                ),
                500,
            )

    @app.delete("/admin/api/photo")
    @login_required
    def admin_delete_photo():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err
        try:
            SitePhoto.query.delete()
            db.session.commit()
            return jsonify({"ok": True})
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Photo delete failed: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Delete failed",
                        "detail": f"{exc.__class__.__name__}: {str(exc)[:200]}",
                    }
                ),
                500,
            )

    @app.post("/admin/api/resume")
    @login_required
    def admin_upload_resume():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err

        if "resume" not in request.files:
            return jsonify({"ok": False, "error": "Missing file field: resume"}), 400

        f = request.files["resume"]
        raw = f.read()
        if not raw:
            return jsonify({"ok": False, "error": "Empty file"}), 400

        locale = normalize_locale(request.form.get("locale", ""))
        mimetype = f.mimetype or "application/pdf"

        try:
            existing = ResumeFile.query.filter_by(locale=locale).first()
            if existing:
                existing.filename = f.filename or f"resume_{locale}.pdf"
                existing.mimetype = mimetype
                existing.bytes = raw
            else:
                db.session.add(
                    ResumeFile(
                        locale=locale,
                        filename=f.filename or f"resume_{locale}.pdf",
                        mimetype=mimetype,
                        bytes=raw,
                    )
                )
            db.session.commit()
            return jsonify({"ok": True})
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Resume upload failed: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Resume upload failed",
                        "detail": f"{exc.__class__.__name__}: {str(exc)[:200]}",
                    }
                ),
                500,
            )

    @app.delete("/admin/api/resume")
    @login_required
    def admin_delete_resume():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err

        locale = normalize_locale(request.args.get("locale", ""))
        try:
            ResumeFile.query.filter_by(locale=locale).delete()
            db.session.commit()
            return jsonify({"ok": True})
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Resume delete failed: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Delete failed",
                        "detail": f"{exc.__class__.__name__}: {str(exc)[:200]}",
                    }
                ),
                500,
            )

    @app.put("/admin/api/links")
    @login_required
    def admin_save_links():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err

        data = request.get_json(force=True, silent=False)
        github = data.get("github", [])
        website = data.get("website", [])

        def validate_list(items: Any, kind: str) -> List[Dict[str, str]]:
            if not isinstance(items, list) or len(items) > 5:
                abort(400)
            out: List[Dict[str, str]] = []
            for it in items:
                if not isinstance(it, dict):
                    abort(400)
                label = (it.get("label") or "").strip()
                url = (it.get("url") or "").strip()
                if not label or not url:
                    abort(400)
                if len(label) > 80 or len(url) > 500:
                    abort(400)
                out.append({"label": label, "url": url, "kind": kind})
            return out

        github_list = validate_list(github, "github")
        website_list = validate_list(website, "website")

        try:
            LinkItem.query.filter_by(kind="github").delete()
            LinkItem.query.filter_by(kind="website").delete()

            for idx, it in enumerate(github_list):
                db.session.add(
                    LinkItem(
                        kind="github",
                        label=it["label"],
                        url=it["url"],
                        sort_order=idx,
                        pair_index=idx,
                    )
                )
            for idx, it in enumerate(website_list):
                db.session.add(
                    LinkItem(
                        kind="website",
                        label=it["label"],
                        url=it["url"],
                        sort_order=idx,
                        pair_index=idx,
                    )
                )

            db.session.commit()
            return jsonify({"ok": True})
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Links save failed: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Save failed",
                        "detail": f"{exc.__class__.__name__}: {str(exc)[:200]}",
                    }
                ),
                500,
            )

    @app.put("/admin/api/accomplishments")
    @login_required
    def admin_save_accomplishments():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err

        data = request.get_json(force=True, silent=False)
        items = data.get("accomplishments", [])
        if not isinstance(items, list) or len(items) > 20:
            abort(400)

        validated: List[str] = []
        for it in items:
            if not isinstance(it, dict):
                abort(400)
            text_val = (it.get("text") or "").strip()
            if not text_val or len(text_val) > 500:
                abort(400)
            validated.append(text_val)

        try:
            Accomplishment.query.delete()
            for idx, text_val in enumerate(validated):
                db.session.add(Accomplishment(text=text_val, sort_order=idx))
            db.session.commit()
            return jsonify({"ok": True})
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Accomplishments save failed: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Save failed",
                        "detail": f"{exc.__class__.__name__}: {str(exc)[:200]}",
                    }
                ),
                500,
            )

    return app


app = create_app()
