import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

logger = logging.getLogger("crowd_safety.database")

Base = declarative_base()

def get_engine():
    # Attempt primary database URL (PostgreSQL)
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3} if "postgresql" in settings.DATABASE_URL else {}
        )
        # Verify connection
        with engine.connect() as conn:
            logger.info("Successfully connected to primary database (PostgreSQL).")
        return engine
    except Exception as e:
        logger.warning(
            f"Unable to connect to primary database ({settings.DATABASE_URL}): {e}. "
            f"Falling back to local SQLite database: {settings.SQLITE_FALLBACK_URL}."
        )
        # Fallback to SQLite
        engine = create_engine(
            settings.SQLITE_FALLBACK_URL,
            connect_args={"check_same_thread": False}
        )
        return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend.app.models import user, camera, setting, events  # ensure models are registered
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")
