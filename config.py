import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY", "prod-healthcare-secret-key-998822")

    # Programmatic credential quotation to handle passwords with special characters (@, $, etc.) safely
    # Use DATABASE_URL if present; on Vercel it's always set via env vars (no DNS check needed)
    _db_url = os.getenv("DATABASE_URL")
    _use_supabase = bool(_db_url)

    if _use_supabase and _db_url:
        try:
            if "://" in _db_url:
                scheme, rest = _db_url.split("://", 1)
                if scheme == "postgres":
                    scheme = "postgresql"

                if "@" in rest:
                    creds, host_db = rest.rsplit("@", 1)
                    if ":" in creds:
                        username, password = creds.split(":", 1)
                        from urllib.parse import quote_plus
                        quoted_password = quote_plus(password)
                        _db_url = f"{scheme}://{username}:{quoted_password}@{host_db}"
                    else:
                        _db_url = f"{scheme}://{creds}@{host_db}"
                else:
                    _db_url = f"{scheme}://{rest}"
        except Exception:
            if _db_url.startswith("postgres://"):
                _db_url = _db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        # No DATABASE_URL → fallback to local SQLite (never used on Vercel)
        if os.environ.get("VERCEL") == "1":
            SQLALCHEMY_DATABASE_URI = "sqlite://"
        else:
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'database' / 'iot_healthcare.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Serverless-safe connection pooling:
    # Vercel Lambda = NullPool (no persistent connections — prevents EMAXCONNSESSION)
    # Local dev = standard pool (5 connections, recycle every 280s)
    if os.environ.get("VERCEL") == "1":
        SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": NullPool,
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_size": 3,
            "max_overflow": 2,
            "pool_recycle": 280,
            "pool_pre_ping": True,
        }

    HR_MIN = 60
    HR_MAX = 100
    HR_WARN_MAX = 120
    HR_CRIT_MAX = 140
    HR_CRIT_MIN = 40

    SPO2_MIN = 95
    SPO2_WARN_MIN = 90
    SPO2_CRIT_MIN = 85

    TEMP_MIN = 36.1
    TEMP_MAX = 37.5
    TEMP_WARN_MIN = 35.5
    TEMP_WARN_MAX = 38.0
    TEMP_CRIT_MIN = 35.0
    TEMP_CRIT_MAX = 39.0

    PREDICTION_CONFIDENCE_THRESHOLD = 0.7
