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
    """Initialize Flask-SQLAlchemy. Falls back to SQLite if cloud DB is unreachable (e.g. Vercel IPv6 block)."""
    db.init_app(app)
    with app.app_context():
        import database.models  # noqa: F401

        try:
            db.create_all()
            logger.info("Database tables created/verified successfully.")
        except Exception as e:
            logger.error(f"Primary DB unreachable: {e}. Switching to SQLite fallback.")
            # Override to in-memory SQLite so the app can start without crashing
            app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
            db.engine.dispose()
            try:
                db.create_all()
                logger.info("Fallback SQLite in-memory DB initialised.")
            except Exception as e2:
                logger.error(f"Fallback SQLite also failed: {e2}")
            return

        # Migration: add new columns (safe — each ignores existing column error)
        for stmt in [
            "ALTER TABLE patients ADD COLUMN blood_group VARCHAR(10)",
            "ALTER TABLE patients ADD COLUMN emergency_contact VARCHAR(200)",
            "ALTER TABLE alert_history ADD COLUMN value FLOAT",
            "ALTER TABLE alert_history ADD COLUMN threshold FLOAT",
        ]:
            try:
                from sqlalchemy import text
                db.session.execute(text(stmt))
                db.session.commit()
            except Exception:
                db.session.rollback()
