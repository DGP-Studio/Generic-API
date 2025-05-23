import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from base_logger import get_logger
import socket


logger = get_logger(__name__)
if "dev" in os.getenv("SERVER_TYPE", "").lower():
    MYSQL_HOST = os.getenv("MYSQL_HOST")
else:
    MYSQL_HOST = socket.gethostbyname('host.docker.internal')
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL,
                       pool_pre_ping=True,
                       pool_recycle=3600,
                       pool_size=10,
                       max_overflow=20
                       )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
logger.info(f"MySQL connection established to {MYSQL_HOST}/{MYSQL_DATABASE}")
