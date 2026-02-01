import os
import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

logger = logging.getLogger(__name__)

# load .env file
load_dotenv()


def get_database_url() -> str:
    """
    Determine database URL based on environment.
    
    Priority:
    1. DATABASE_URL environment variable (for local dev with explicit URL)
    2. AWS Secrets Manager (if AWS_REGION and DB_SECRET_NAME are set)
    3. SQLite fallback
    """
    # Check for explicit DATABASE_URL
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        logger.info("Using DATABASE_URL from environment")
        return explicit_url
    
    # Check for AWS configuration
    aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    secret_name = os.getenv("DB_SECRET_NAME")
    
    if aws_region and secret_name:
        logger.info(f"Fetching database credentials from Secrets Manager: {secret_name}")
        try:
            from app.secrets import get_secret, build_database_url_from_secret
            secret = get_secret(aws_region, secret_name)
            db_url = build_database_url_from_secret(secret)
            logger.info("Successfully retrieved database credentials from Secrets Manager")
            return db_url
        except Exception as e:
            logger.error(f"Failed to get credentials from Secrets Manager: {e}", exc_info=True)
            logger.warning("Falling back to SQLite")
    
    # Fallback to SQLite
    sqlite_url = "sqlite:///./openmemory.db"
    logger.info(f"Using SQLite: {sqlite_url}")
    return sqlite_url


DATABASE_URL = get_database_url()

# SQLite-specific optimization: Enable WAL mode for better concurrency
def configure_sqlite_for_concurrency(dbapi_conn, connection_record):
    """Enable SQLite WAL mode and set busy timeout"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
    cursor.close()

# SQLAlchemy engine
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=5,
    max_overflow=10
)

# Apply SQLite optimizations if using SQLite
if DATABASE_URL.startswith("sqlite"):
    event.listen(engine, "connect", configure_sqlite_for_concurrency)

# Session factory for FastAPI requests (request-scoped)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Scoped session for background workers (thread-local)
ScopedSession = scoped_session(SessionLocal)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI (request-scoped sessions)
def get_db():
    """FastAPI dependency for request-scoped database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function for background workers (thread-local scoped session)
def get_worker_db():
    """
    Get thread-local database session for background workers.
    
    Each worker thread gets its own session that persists across calls
    within that thread. Workers must call remove_worker_db() when done.
    
    Returns:
        scoped_session: Thread-local database session
    """
    return ScopedSession()

def remove_worker_db():
    """
    Remove thread-local session for current thread.
    
    Should be called by workers when done with database operations
    to clean up resources and avoid session leaks.
    """
    ScopedSession.remove()
