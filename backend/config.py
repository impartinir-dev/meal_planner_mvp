import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-for-docker")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
