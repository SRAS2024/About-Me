from __future__ import annotations

import re
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

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
from io import BytesIO

from config import Config
from i18n import babel, select_locale
from models import db, LinkItem, ResumeFile, SitePhoto
from services.image_processing import compress_image


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    babel.init_app(app, locale_selector=lambda: select_locale(app))

    with app.app_context():
        db.create_all()

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
        # Allow en, pt, pt_BR, fr, etc; sanitize
        if not re.fullmatch(r"[A-Za-z]{2}([_-][A-Za-z]{2})?", loc):
            return app.config.get("BABEL_DEFAULT_LOCALE", "en")
        return loc.replace("-", "_")

    def best_resume_locale() -> str:
        # Prefer exact supported locales if uploaded
        available = [r.locale for r in ResumeFile.query.all()]
        if not available:
            return app.config.get("BABEL_DEFAULT_LOCALE", "en")

        best = request.accept_languages.best_match(available)
        if best:
            return best

        # Also try base language match (pt vs pt_BR)
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
            {"id": i.id, "kind": i.kind, "label": i.label, "url": i.url, "sort_order": i.sort_order}
            for i in items
        ]

    @app.get("/")
    def index():
        photo_exists = SitePhoto.query.first() is not None
        locale = select_locale(app)

        resume_locale = best_resume_locale()
        has_resume = ResumeFile.query.filter_by(locale=resume_locale).first() is not None

        github_links = get_links("github")
        website_links = get_links("website")

        return render_template(
            "index.html",
            locale=locale,
            photo_exists=photo_exists,
            resume_locale=resume_locale,
            has_resume=has_resume,
            github_links=github_links,
            website_links=website_links,
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
            # Choose best based on browser language
            best = best_resume_locale()
            resume = ResumeFile.query.filter_by(locale=best).first()
        if not resume:
            abort(404)
        return send_file(BytesIO(resume.bytes), mimetype=resume.mimetype, download_name=resume.filename)

    @app.get("/admin")
    @login_required
    def admin():
        photo_exists = SitePhoto.query.first() is not None
        locale = select_locale(app)

        # Provide current best resume locale for preview; admin can upload others
        resume_locale = best_resume_locale()
        has_resume = ResumeFile.query.filter_by(locale=resume_locale).first() is not None

        github_links = get_links("github")
        website_links = get_links("website")

        return render_template(
            "admin.html",
            locale=locale,
            photo_exists=photo_exists,
            resume_locale=resume_locale,
            has_resume=has_resume,
            github_links=github_links,
            website_links=website_links,
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

        return render_template("admin_login.html", next=request.form.get("next", "/admin"), error=_("Invalid login."))

    @app.post("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("index"))

    # Admin APIs

    @app.get("/admin/api/state")
    @login_required
    def admin_state():
        photo_exists = SitePhoto.query.first() is not None
        resumes = ResumeFile.query.order_by(ResumeFile.locale.asc()).all()
        return jsonify(
            {
                "photo_exists": photo_exists,
                "resumes": [{"locale": r.locale, "filename": r.filename} for r in resumes],
                "github_links": get_links("github"),
                "website_links": get_links("website"),
            }
        )

    @app.post("/admin/api/photo")
    @login_required
    def admin_upload_photo():
        if "photo" not in request.files:
            abort(400)

        f = request.files["photo"]
        raw = f.read()
        if not raw:
            abort(400)

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

    @app.delete("/admin/api/photo")
    @login_required
    def admin_delete_photo():
        SitePhoto.query.delete()
        db.session.commit()
        return jsonify({"ok": True})

    @app.post("/admin/api/resume")
    @login_required
    def admin_upload_resume():
        if "resume" not in request.files:
            abort(400)
        f = request.files["resume"]
        raw = f.read()
        if not raw:
            abort(400)

        locale = normalize_locale(request.form.get("locale", ""))
        mimetype = f.mimetype or "application/pdf"

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

    @app.delete("/admin/api/resume")
    @login_required
    def admin_delete_resume():
        locale = normalize_locale(request.args.get("locale", ""))
        ResumeFile.query.filter_by(locale=locale).delete()
        db.session.commit()
        return jsonify({"ok": True})

    @app.put("/admin/api/links")
    @login_required
    def admin_save_links():
        data = request.get_json(force=True, silent=False)
        github = data.get("github", [])
        website = data.get("website", [])

        def validate_list(items: Any, kind: str) -> List[Dict[str, str]]:
            if not isinstance(items, list):
                abort(400)
            if len(items) > 5:
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

        # Replace all of each kind
        LinkItem.query.filter_by(kind="github").delete()
        LinkItem.query.filter_by(kind="website").delete()

        for idx, it in enumerate(github_list):
            db.session.add(LinkItem(kind="github", label=it["label"], url=it["url"], sort_order=idx))
        for idx, it in enumerate(website_list):
            db.session.add(LinkItem(kind="website", label=it["label"], url=it["url"], sort_order=idx))

        db.session.commit()
        return jsonify({"ok": True})

    return app


app = create_app()
