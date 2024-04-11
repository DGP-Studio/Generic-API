from .database import Base
from sqlalchemy import Column, Integer, String, Date


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


class AvatarStrategy(Base):
    __tablename__ = "avatar_strategies"

    id = Column(Integer, primary_key=True, index=True)
    avatar_id = Column(Integer, index=True)
    mys_strategy_id = Column(Integer, nullable=True)
    hoyolab_strategy_id = Column(Integer, nullable=True)

    def __repr__(self):
        return (f"<AvatarStrategy(avatar_id={self.avatar_id}, mys_strategy_id={self.mys_strategy_id}, "
                f"hoyolab_strategy_id={self.hoyolab_strategy_id})>")
