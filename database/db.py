from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
import logging

logger = logging.getLogger(__name__)

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

db = SQLAlchemy(metadata=metadata)


def init_db(app):
    """Initialize Flask-SQLAlchemy directly connected to Supabase."""
    db.init_app(app)
    # We do NOT run db.create_all() or migration alters here to prevent Vercel startup latency
    # and connection locks. Tables are created directly in Supabase using SQL Editor.
    logger.info("Flask-SQLAlchemy initialized for Supabase.")
