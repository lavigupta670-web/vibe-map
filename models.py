from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_photo = db.Column(db.String(256), default='default_profile.png')
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    vibe_checks = db.relationship('VibeCheck', backref='user', lazy='dynamic')
    saved_places = db.relationship('SavedPlace', backref='user', lazy='dynamic')
    reports = db.relationship('Report', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Place(db.Model):
    __tablename__ = 'places'
    id = db.Column(db.Integer, primary_key=True)
    google_place_id = db.Column(db.String(200), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(500))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    google_rating = db.Column(db.Float)
    price_level = db.Column(db.Integer)
    photo_reference = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    vibe_checks = db.relationship('VibeCheck', backref='place', lazy='dynamic')
    saved_by = db.relationship('SavedPlace', backref='place', lazy='dynamic')

    @property
    def vibe_score(self):
        checks = self.vibe_checks.all()
        if not checks:
            return None
        avg = sum(c.rating for c in checks) / len(checks)
        score = int(avg * 20)
        count = len(checks)
        if count <= 4:
            score = int(score * 0.6)
        elif count <= 19:
            score = int(score * 0.85)
        return min(score, 100)

    @property
    def vibe_score_label(self):
        count = self.vibe_checks.count()
        if count == 0:
            return 'NO VIBES YET'
        if count <= 4:
            return 'NEW VIBE'
        if count <= 19:
            return 'EMERGING VIBE'
        return 'TRUSTED VIBE'

    @property
    def vibe_check_count(self):
        return self.vibe_checks.count()


class VibeCheck(db.Model):
    __tablename__ = 'vibe_checks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.String(300), default='')
    photo_filename = db.Column(db.String(256), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    location_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tags = db.relationship('VibeTag', secondary='vibe_check_tags', backref='vibe_checks', lazy='dynamic')
    reports = db.relationship('Report', backref='vibe_check', lazy='dynamic')


class VibeTag(db.Model):
    __tablename__ = 'vibe_tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    emoji = db.Column(db.String(10), default='')


class VibeCheckTag(db.Model):
    __tablename__ = 'vibe_check_tags'
    id = db.Column(db.Integer, primary_key=True)
    vibe_check_id = db.Column(db.Integer, db.ForeignKey('vibe_checks.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('vibe_tags.id'), nullable=False)


class SavedPlace(db.Model):
    __tablename__ = 'saved_places'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('user_id', 'place_id'),)


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    vibe_check_id = db.Column(db.Integer, db.ForeignKey('vibe_checks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))