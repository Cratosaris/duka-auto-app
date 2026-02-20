import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://duka_user:duka_pass_2024@db:5432/duka_auto')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    LOGO_FOLDER = os.path.join(UPLOAD_FOLDER, 'logos')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # App
    GARAGE_NAME_DEFAULT = "Duka Auto"
    DEVISE = "FBu"
    LANGUE = "fr"
