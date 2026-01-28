from __future__ import annotations

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint

db = SQLAlchemy()


class SitePhoto(db.Model):
    __tablename__ = "site_photo"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.Text, nullable=False)
    mimetype = db.Column(db.Text, nullable=False)
    bytes = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ResumeFile(db.Model):
    __tablename__ = "resume_file"

    id = db.Column(db.Integer, primary_key=True)
    locale = db.Column(db.Text, nullable=False)
    filename = db.Column(db.Text, nullable=False)
    mimetype = db.Column(db.Text, nullable=False)
    bytes = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("locale", name="uq_resume_locale"),
    )


class LinkItem(db.Model):
    __tablename__ = "link_item"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.Text, nullable=False)  # "github" or "website"
    label = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    pair_index = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("kind in ('github','website')", name="ck_link_kind"),
    )


class Accomplishment(db.Model):
    __tablename__ = "accomplishment"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
