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

    def dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.Wallpaper({self.dict()})"


class AvatarStrategy(Base):
    __tablename__ = "avatar_strategies"

    id = Column(Integer, primary_key=True, index=True)
    avatar_id = Column(Integer, index=True)
    mys_strategy_id = Column(Integer, nullable=True)
    hoyolab_strategy_id = Column(Integer, nullable=True)

    def dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.AvatarStrategy({self.dict()})"


class DailyActiveUserStats(Base):
    __tablename__ = "active_user_stats"

    date = Column(Date, primary_key=True, index=True)
    cn_user = Column(Integer, nullable=False)
    global_user = Column(Integer, nullable=False)
    unknown = Column(Integer, nullable=False)

    def dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.DailyActiveUserStats({self.dict()})"


class DailyEmailSentStats(Base):
    __tablename__ = "email_sent_stats"

    date = Column(Date, primary_key=True, index=True)
    requested = Column(Integer, nullable=False)
    sent = Column(Integer, nullable=False)
    failed = Column(Integer, nullable=False)

    def dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.DailyEmailSentStats({self.dict()})"
