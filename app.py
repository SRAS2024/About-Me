from __future__ import annotations

import hmac
import logging
import os
import re
import time
import traceback
from datetime import datetime
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
from models import db, Accomplishment, ContactMessage, LinkItem, ResumeFile, SitePhoto, Trait
from services.image_processing import compress_image

logger = logging.getLogger(__name__)

# Public pages shown in the site navigation, in menu order.
# "i18n" is the key the label translator in static/js/i18n.js uses.
NAV_PAGES = [
    {"endpoint": "index", "label": "Home", "i18n": "home"},
    {"endpoint": "about", "label": "About", "i18n": "about"},
    {"endpoint": "experience", "label": "Experience", "i18n": "experience"},
    {"endpoint": "skills", "label": "Education & Skills", "i18n": "skills"},
    {"endpoint": "contact", "label": "Contact", "i18n": "contact"},
]

# Contact form choices (value -> label). Validated on the server as well as in the browser.
CONTACT_REASONS = {
    "job": "Job opportunity",
    "freelance": "Freelance project",
    "networking": "Networking",
    "other": "Something else",
}
# Local part may not contain characters that change a mailto: link (?, &, =, %, #, /);
# the domain must be a real hostname with a letter-only top-level domain.
EMAIL_RE = re.compile(
    r"^[^\s@?#&=%/]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$"
)
# Control characters (except tab and newlines) are dropped; PostgreSQL rejects NUL in text.
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
CONTACT_LIMITS = {"name": 80, "email": 254, "company": 100, "message": 2000}
MESSAGE_MIN_CHARS = 20


def validate_contact(data: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, str]]:
    """
    Returns (clean_values, errors). errors maps a field name to a message the
    form can show next to that field. Mirrors the checks in static/js/site.js.
    """

    def field(key: str) -> str:
        val = data.get(key)
        return CONTROL_CHARS_RE.sub("", val).strip() if isinstance(val, str) else ""

    clean = {key: field(key) for key in ("name", "email", "company", "reason", "message")}
    errors: Dict[str, str] = {}

    name = clean["name"]
    if not name:
        errors["name"] = "Please enter your name."
    elif len(name) < 2:
        errors["name"] = "Your name should be at least 2 characters."
    elif len(name) > CONTACT_LIMITS["name"]:
        errors["name"] = "Please keep your name under 80 characters."
    elif any(ch.isdigit() for ch in name):
        errors["name"] = "Names can't include numbers."

    email = clean["email"]
    if not email:
        errors["email"] = "Please enter your email address."
    elif len(email) > CONTACT_LIMITS["email"] or not EMAIL_RE.match(email):
        errors["email"] = "Please enter a valid email address, like name@example.com."

    if len(clean["company"]) > CONTACT_LIMITS["company"]:
        errors["company"] = "Please keep the company name under 100 characters."

    if clean["reason"] not in CONTACT_REASONS:
        errors["reason"] = "Please choose a reason for reaching out."

    message = clean["message"]
    if not message:
        errors["message"] = "Please write a short message."
    elif len(message) < MESSAGE_MIN_CHARS:
        errors["message"] = "Please write at least 20 characters so I know how to help."
    elif len(message) > CONTACT_LIMITS["message"]:
        errors["message"] = "Please keep your message under 2,000 characters."

    consent = data.get("consent")
    if consent not in (True, "on", "true", "1", "yes"):
        errors["consent"] = "Please confirm it's okay to store your message so I can reply."

    return clean, errors


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    babel.init_app(app, locale_selector=lambda: select_locale(app))

    # Session cookie hardening. Flask already defines these keys, so setdefault() would not
    # change them; assign directly. Railway serves HTTPS only (HTTP redirects), so mark the
    # cookie Secure there and leave it off for local http://localhost development.
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

    # Single source of truth for limits used by the backend
    MAX_TRAITS = 12

    def is_logged_in() -> bool:
        return session.get("admin_authed") is True

    def safe_next(target: str) -> str:
        # Only follow same-site paths after login ("//evil.com" and "https://..." are rejected).
        target = (target or "").strip()
        if (
            target.startswith("/")
            and not target.startswith("//")
            and "\\" not in target
            and not any(ord(ch) < 32 for ch in target)
        ):
            return target
        return url_for("admin")

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not is_logged_in():
                # API calls get JSON so the admin page can report it, instead of a login page.
                if request.path.startswith("/admin/api/"):
                    return jsonify({"ok": False, "error": "Not logged in. Please sign in again."}), 401
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
        default = app.config.get("BABEL_DEFAULT_LOCALE", "en")
        available = [r.locale for r in ResumeFile.query.order_by(ResumeFile.locale.asc()).all()]
        if not available:
            return default
        best = request.accept_languages.best_match(available)
        if best:
            return best
        accept = [lang for lang, _q in request.accept_languages]
        for lang in accept:
            base = lang.split("-")[0].split("_")[0]
            for a in available:
                if a.split("_")[0] == base:
                    return a
        return default if default in available else available[0]

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

    # The bare domain forwards to the main www address, keeping the path and query.
    @app.before_request
    def redirect_bare_domain():
        host = (request.host or "").split(":")[0].lower()
        if host == "ssimonds.com":
            return redirect("https://www.ssimonds.com" + request.full_path.rstrip("?"), code=301)
        return None

    # Browsers ask for /favicon.ico on their own; point them at the SVG icon.
    @app.get("/favicon.ico")
    def favicon():
        return redirect(url_for("static", filename="images/favicon.svg"), code=301)

    # ── Search engines ────────────────────────────────────────────
    # Public URLs always use the main domain so Google indexes one address per page.
    SITE_URL = os.environ.get("SITE_URL", "https://www.ssimonds.com").rstrip("/")

    @app.get("/robots.txt")
    def robots_txt():
        body = f"User-agent: *\nDisallow: /admin\nDisallow: /api/\n\nSitemap: {SITE_URL}/sitemap.xml\n"
        return app.response_class(body, mimetype="text/plain")

    # Google Search Console ownership file (HTML file verification method, account samuelrasimonds@gmail.com).
    GOOGLE_VERIFICATION_FILE = "google0292583cfdf40074.html"

    @app.get(f"/{GOOGLE_VERIFICATION_FILE}")
    def google_site_verification():
        return app.response_class(
            f"google-site-verification: {GOOGLE_VERIFICATION_FILE}", mimetype="text/html"
        )

    @app.get("/sitemap.xml")
    def sitemap_xml():
        paths = ["/"] + [url_for(p["endpoint"]) for p in NAV_PAGES if p["endpoint"] != "index"]
        urls = "".join(f"  <url><loc>{SITE_URL}{path}</loc></url>\n" for path in paths)
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}</urlset>\n"
        )
        return app.response_class(body, mimetype="application/xml")

    # ── Public Routes ─────────────────────────────────────────────

    @app.context_processor
    def inject_site_globals() -> Dict[str, Any]:
        active = request.endpoint
        if active == "index_html":
            active = "index"
        elif active == "contact_post":
            active = "contact"
        # One canonical address per page (the Railway URL also serves the site).
        path = "/" if request.path == "/index.html" else request.path
        canonical_url = os.environ.get("SITE_URL", "https://www.ssimonds.com").rstrip("/") + path
        return {
            "nav_pages": NAV_PAGES,
            "active_page": active,
            "current_year": datetime.now().year,
            "canonical_url": canonical_url,
        }

    # ── Contact form throttle (per visitor, in memory) ────────────
    contact_hits: Dict[str, List[float]] = {}
    CONTACT_WINDOW_SECONDS = 600
    CONTACT_MAX_PER_WINDOW = 5

    def client_ip() -> str:
        # Railway's edge proxy appends the real visitor address as the LAST X-Forwarded-For
        # entry; anything before it was sent by the client and could be faked.
        forwarded = request.headers.get("X-Forwarded-For", "")
        last = forwarded.split(",")[-1].strip() if forwarded else ""
        return last or (request.remote_addr or "unknown")

    def contact_rate_limited() -> bool:
        now = time.time()
        if len(contact_hits) > 1000:
            for key in [k for k, v in contact_hits.items() if not v or now - v[-1] > CONTACT_WINDOW_SECONDS]:
                contact_hits.pop(key, None)
        ip = client_ip()
        recent = [t for t in contact_hits.get(ip, []) if now - t < CONTACT_WINDOW_SECONDS]
        limited = len(recent) >= CONTACT_MAX_PER_WINDOW
        if not limited:
            recent.append(now)
        contact_hits[ip] = recent
        return limited

    def save_contact_message(clean: Dict[str, str]) -> None:
        db.session.add(
            ContactMessage(
                name=clean["name"],
                email=clean["email"],
                company=clean["company"],
                reason=clean["reason"],
                message=clean["message"],
            )
        )
        db.session.commit()

    @app.get("/")
    def index():
        locale = select_locale(app)
        try:
            photo_exists = SitePhoto.query.first() is not None
            resume_locale = best_resume_locale()
            has_resume = ResumeFile.query.filter_by(locale=resume_locale).first() is not None
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
                accomplishments=[],
                traits=[],
            )

        return render_template(
            "index.html",
            locale=locale,
            photo_exists=photo_exists,
            resume_locale=resume_locale,
            has_resume=has_resume,
            accomplishments=accomplishments,
            traits=traits,
        )

    # The homepage is also reachable by its file name.
    @app.get("/index.html")
    def index_html():
        return index()

    @app.get("/about.html")
    def about():
        return render_template("about.html")

    @app.get("/experience.html")
    def experience():
        return render_template("experience.html")

    @app.get("/skills.html")
    def skills():
        return render_template("skills.html")

    # The Projects page was retired; send old links and bookmarks to the homepage.
    @app.get("/projects.html")
    @app.get("/projects")
    def projects_retired():
        return redirect(url_for("index"), code=301)

    @app.get("/contact.html")
    def contact():
        return render_template("contact.html", form={}, errors={}, sent=False, reasons=CONTACT_REASONS)

    # Fallback for browsers without JavaScript: a normal form POST that re-renders the page.
    @app.post("/contact.html")
    def contact_post():
        data = request.form.to_dict()
        if (data.get("website") or "").strip():
            # Honeypot field was filled in, so this is a bot. Act as if it worked.
            return render_template("contact.html", form={}, errors={}, sent=True, reasons=CONTACT_REASONS)
        clean, errors = validate_contact(data)
        if not errors and contact_rate_limited():
            errors["form"] = "You've sent several messages in a short time. Please try again in a few minutes."
        if not errors:
            try:
                save_contact_message(clean)
            except Exception as exc:
                db.session.rollback()
                app.logger.error("Contact save failed: %s\n%s", exc, traceback.format_exc())
                errors["form"] = "Your message couldn't be saved right now. Please email me directly instead."
        if errors:
            # Keep the consent box ticked on the re-rendered form if it was ticked.
            form = dict(clean, consent=data.get("consent") in ("on", "true", "1", "yes"))
            return (
                render_template(
                    "contact.html", form=form, errors=errors, sent=False, reasons=CONTACT_REASONS
                ),
                400,
            )
        return render_template("contact.html", form={}, errors={}, sent=True, reasons=CONTACT_REASONS)

    # JSON endpoint used by the contact form script (static/js/site.js).
    @app.post("/api/contact")
    def api_contact():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "Invalid request."}), 400
        honeypot = data.get("website")
        if isinstance(honeypot, str) and honeypot.strip():
            return jsonify({"ok": True}), 201
        clean, errors = validate_contact(data)
        if errors:
            return jsonify({"ok": False, "error": "Please fix the highlighted fields.", "errors": errors}), 400
        if contact_rate_limited():
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "You've sent several messages in a short time. Please try again in a few minutes.",
                    }
                ),
                429,
            )
        try:
            save_contact_message(clean)
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Contact save failed: %s\n%s", exc, traceback.format_exc())
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Your message couldn't be saved right now. Please email me directly instead.",
                    }
                ),
                503,
            )
        return jsonify({"ok": True}), 201

    # Short addresses without ".html" send visitors to the real page.
    for slug in ("about", "experience", "skills", "contact"):
        app.add_url_rule(
            f"/{slug}",
            f"{slug}_short",
            lambda slug=slug: redirect(url_for(slug), code=301),
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
        expected_user = app.config.get("ADMIN_USERNAME") or ""
        expected_pass = app.config.get("ADMIN_PASSWORD") or ""
        # Login is disabled until both values are set in the environment.
        if (
            expected_user
            and expected_pass
            and hmac.compare_digest(username.encode(), expected_user.encode())
            and hmac.compare_digest(password.encode(), expected_pass.encode())
        ):
            session["admin_authed"] = True
            return redirect(safe_next(request.form.get("next", "")))
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

        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "Invalid request body"}), 400
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

        # Only real PDFs: the file is served inline from this site, so never trust the
        # browser-supplied content type (an HTML "resume" would run as a page here).
        if b"%PDF-" not in raw[:1024]:
            return jsonify({"ok": False, "error": "Resume must be a PDF file"}), 400

        locale = normalize_locale(request.form.get("locale", ""))
        mimetype = "application/pdf"

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

        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            abort(400)
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
                if not label and not url:
                    continue  # an untouched blank row
                if not label or not url:
                    abort(400)
                if url.startswith("//"):
                    url = "https:" + url
                if not re.match(r"^https?://", url, re.IGNORECASE):
                    # Block javascript:, data: and other schemes; treat "github.com/x" as https.
                    if re.match(r"^[a-z][a-z0-9+.-]*:(?!\d)", url, re.IGNORECASE):
                        abort(400)
                    url = "https://" + url.lstrip("/")
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

        data = request.get_json(force=True, silent=True)
        if not isinstance(data, dict):
            abort(400)
        items = data.get("accomplishments", [])
        if not isinstance(items, list) or len(items) > 20:
            abort(400)

        validated: List[str] = []
        for it in items:
            if not isinstance(it, dict):
                abort(400)
            text_val = (it.get("text") or "").strip()
            if not text_val:
                continue  # an untouched blank row
            if len(text_val) > 500:
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

    @app.get("/admin/api/messages")
    @login_required
    def admin_messages():
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err
        try:
            items = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(200).all()
            return jsonify(
                {
                    "messages": [
                        {
                            "id": m.id,
                            "name": m.name,
                            "email": m.email,
                            "company": m.company,
                            "reason": CONTACT_REASONS.get(m.reason, m.reason),
                            "message": m.message,
                            "created_at": m.created_at.isoformat() + "Z",
                        }
                        for m in items
                    ]
                }
            )
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Loading messages failed: %s\n%s", exc, traceback.format_exc())
            return jsonify({"ok": False, "error": "Failed to load messages"}), 500

    @app.delete("/admin/api/messages/<int:message_id>")
    @login_required
    def admin_delete_message(message_id: int):
        db_err = require_db_or_503()
        if db_err is not None:
            return db_err
        try:
            ContactMessage.query.filter_by(id=message_id).delete()
            db.session.commit()
            return jsonify({"ok": True})
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Message delete failed: %s\n%s", exc, traceback.format_exc())
            return jsonify({"ok": False, "error": "Delete failed"}), 500

    return app


app = create_app()
