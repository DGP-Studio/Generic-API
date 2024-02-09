from .database import Base
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date


class Wallpaper(Base):
    __tablename__ = "wallpapers"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    display_date = Column(Date, index=True, nullable=True)
    last_display_date = Column(Date, index=True, nullable=True)
    source_url = Column(String, index=True)
    author = Column(String, index=True)
    uploader = Column(String, index=True)
    disabled = Column(Integer, default=False)
