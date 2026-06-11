import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-not-for-production")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
STATIC_DIR = os.environ.get("STATIC_DIR", "")
COOKIE_NAME = "mib_session"
TOKEN_TTL_SECONDS = 7 * 24 * 3600
