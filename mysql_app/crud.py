from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert
from sqlalchemy import or_
from datetime import date, timedelta
from . import models, schemas
from typing import cast
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from base_logger import logger


@contextmanager
def get_db_session(db: Session):
    """
    Context manager for handling database session lifecycle.

    :param db: SQLAlchemy session object
    """
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise e


def get_all_wallpapers(db: Session) -> list[models.Wallpaper]:
    with get_db_session(db):
        return cast(list[models.Wallpaper], db.query(models.Wallpaper).all())


def add_wallpaper(db: Session, wallpaper: schemas.Wallpaper) -> models.Wallpaper:
    with get_db_session(db) as session:
        wallpaper_exists = check_wallpaper_exists(session, wallpaper)
        if wallpaper_exists:
            return wallpaper_exists

        db_wallpaper = models.Wallpaper(**wallpaper.model_dump())
        session.add(db_wallpaper)
        session.flush()
        session.refresh(db_wallpaper)
        return db_wallpaper


def check_wallpaper_exists(db: Session, wallpaper: schemas.Wallpaper) -> models.Wallpaper | None:
    """
    Check if wallpaper with given URL exists in the database. Supporting function for add_wallpaper to check duplicate entries.

    :param db: SQLAlchemy session object

    :param wallpaper: Wallpaper object to be checked
    """
    with get_db_session(db):
        return db.query(models.Wallpaper).filter(models.Wallpaper.url == wallpaper.url).first()


def disable_wallpaper_with_url(db: Session, url: str) -> models.Wallpaper:
    """
    Disable wallpaper with given URL.

    :param db: SQLAlchemy session object

    :param url: URL of the wallpaper to be disabled
    """
    with get_db_session(db) as session:
        session.query(models.Wallpaper).filter(models.Wallpaper.url == url).update({models.Wallpaper.disabled: 1})
        return cast(models.Wallpaper, session.query(models.Wallpaper).filter(models.Wallpaper.url == url).first())


def enable_wallpaper_with_url(db: Session, url: str) -> models.Wallpaper:
    """
    Enable wallpaper with given URL.

    :param db: SQLAlchemy session object

    :param url: URL of the wallpaper to be enabled
    """
    with get_db_session(db) as session:
        session.query(models.Wallpaper).filter(models.Wallpaper.url == url).update({models.Wallpaper.disabled: 0})
        return cast(models.Wallpaper, session.query(models.Wallpaper).filter(models.Wallpaper.url == url).first())


def get_all_fresh_wallpaper(db: Session) -> list[models.Wallpaper]:
    with get_db_session(db) as session:
        target_date = date.today() - timedelta(days=14)
        fresh_wallpapers = session.query(models.Wallpaper).filter(
            or_(
                models.Wallpaper.last_display_date < target_date,
                models.Wallpaper.last_display_date.is_(None)
            )
        ).all()

        # If no fresh wallpapers found, return all wallpapers
        if len(fresh_wallpapers) == 0:
            return cast(list[models.Wallpaper], session.query(models.Wallpaper).all())
        return cast(list[models.Wallpaper], fresh_wallpapers)


def set_last_display_date_with_index(db: Session, index: int) -> models.Wallpaper:
    with get_db_session(db) as session:
        session.query(models.Wallpaper).filter(models.Wallpaper.id == index).update(
            {models.Wallpaper.last_display_date: date.today()})
        result = cast(models.Wallpaper, session.query(models.Wallpaper).filter(models.Wallpaper.id == index).first())
        assert result is not None, "Wallpaper not found"
        return result

def reset_last_display(db: Session) -> bool:
    with get_db_session(db) as session:
        result = session.query(models.Wallpaper).update({models.Wallpaper.last_display_date: None})
        assert result is not None, "Wallpaper not found"
        return True


def add_avatar_strategy(db: Session, strategy: schemas.AvatarStrategy) -> schemas.AvatarStrategy:
    with get_db_session(db) as session:
        insert_stmt = insert(models.AvatarStrategy).values(**strategy.model_dump()).on_duplicate_key_update(
            mys_strategy_id=strategy.mys_strategy_id if strategy.mys_strategy_id is not None else models.AvatarStrategy.mys_strategy_id,
            hoyolab_strategy_id=strategy.hoyolab_strategy_id if strategy.hoyolab_strategy_id is not None else models.AvatarStrategy.hoyolab_strategy_id
        )
        session.execute(insert_stmt)
        return strategy


def get_avatar_strategy_by_id(avatar_id: str, db: Session) -> models.AvatarStrategy | None:
    return db.query(models.AvatarStrategy).filter_by(avatar_id=avatar_id).first()


def get_all_avatar_strategy(db: Session) -> list[models.AvatarStrategy] | None:
    with get_db_session(db) as session:
        result = session.query(models.AvatarStrategy).all()
        if len(result) == 0:
            return None
        return cast(list[models.AvatarStrategy], result)


def dump_daily_active_user_stats(db: Session, stats: schemas.DailyActiveUserStats) -> schemas.DailyActiveUserStats:
    with get_db_session(db) as session:
        db_stats = models.DailyActiveUserStats(**stats.model_dump())
        session.add(db_stats)
        session.flush()
        session.refresh(db_stats)
        return db_stats


def dump_daily_email_sent_stats(db: Session, stats: schemas.DailyEmailSentStats) -> schemas.DailyEmailSentStats:
    with get_db_session(db) as session:
        db_stats = models.DailyEmailSentStats(**stats.model_dump())
        session.add(db_stats)
        session.flush()
        session.refresh(db_stats)
        return db_stats
