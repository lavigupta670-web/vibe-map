import os

# Load .env manually to avoid python-dotenv BOM/encoding issues
try:
    with open('.env', 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if '=' in line and line and not line.startswith('#'):
                key, _, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()
except:
    pass

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///vibe_map.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY', '')
    LOCATION_VERIFY_RADIUS = int(os.environ.get('LOCATION_VERIFY_RADIUS', 200))
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    PER_PAGE = 20
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '')
    TELEGRAM_SECRET_TOKEN = os.environ.get('TELEGRAM_SECRET_TOKEN', '')  # ← ADD THIS
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')
    CLOUDINARY_FOLDER = os.environ.get('CLOUDINARY_FOLDER', 'vibemap')
    
    # App URL for Telegram buttons
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')