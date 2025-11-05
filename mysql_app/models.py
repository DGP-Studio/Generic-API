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

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.Wallpaper(id={self.id}, url={self.url}, last_display_date={self.last_display_date})"


class AvatarStrategy(Base):
    __tablename__ = "avatar_strategies"

    id = Column(Integer, primary_key=True, index=True)
    avatar_id = Column(Integer, index=True)
    mys_strategy_id = Column(Integer, nullable=True)
    hoyolab_strategy_id = Column(Integer, nullable=True)

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.AvatarStrategy({self.__dict__()})"


class DailyActiveUserStats(Base):
    __tablename__ = "active_user_stats"

    date = Column(Date, primary_key=True, index=True)
    cn_user = Column(Integer, nullable=False)
    global_user = Column(Integer, nullable=False)
    unknown = Column(Integer, nullable=False)

    def __dict__(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.DailyActiveUserStats({self.__dict__()})"


class DailyEmailSentStats(Base):
    __tablename__ = "email_sent_stats"

    date = Column(Date, primary_key=True, index=True)
    requested = Column(Integer, nullable=False)
    sent = Column(Integer, nullable=False)
    failed = Column(Integer, nullable=False)

    def __dict__(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.DailyEmailSentStats({self.__dict__()})"


class GitRepository(Base):
    __tablename__ = "git_repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    web_url = Column(String(512), nullable=False)
    https_url = Column(String(512), nullable=True)
    ssh_url = Column(String(512), nullable=True)
    type = Column(String(50), nullable=True)
    token = Column(String(512), nullable=True)

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}

    def __repr__(self):
        return f"models.GitRepository(id={self.id}, name={self.name}, web_url={self.web_url})"
