"""
Database initialization module for creating tables.
"""
from mysql_app.database import engine, Base
from base_logger import get_logger


logger = get_logger(__name__)


def init_database():
    """
    Initialize the database by creating all tables defined in the models.
    This function is idempotent - it will only create tables that don't exist.
    
    Raises:
        Exception: If table creation fails
    """
    try:
        # Import models to register them with SQLAlchemy Base
        from mysql_app import models  # noqa: F401
        
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


if __name__ == "__main__":
    init_database()
    print("Database initialization complete")
