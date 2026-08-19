import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///vibe_map.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY', '')
    LOCATION_VERIFY_RADIUS = int(os.environ.get('LOCATION_VERIFY_RADIUS', 200))
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    PER_PAGE = 20