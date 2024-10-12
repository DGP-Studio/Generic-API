from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert
from sqlalchemy import or_
from datetime import date, timedelta
from . import models, schemas


def get_all_wallpapers(db: Session) -> list[models.Wallpaper]:
    return db.query(models.Wallpaper).all()


def add_wallpaper(db: Session, wallpaper: schemas.Wallpaper) -> models.Wallpaper:
    try:
        wallpaper_exists = check_wallpaper_exists(db, wallpaper)
        if wallpaper_exists:
            return wallpaper_exists
        db_wallpaper = models.Wallpaper(**wallpaper.dict())
        db.add(db_wallpaper)
        db.commit()
        db.refresh(db_wallpaper)
        return db_wallpaper
    except Exception as e:
        db.rollback()
        raise e


def check_wallpaper_exists(db: Session, wallpaper: schemas.Wallpaper) -> models.Wallpaper | None:
    return db.query(models.Wallpaper).filter(models.Wallpaper.url == wallpaper.url).first()


def disable_wallpaper_with_url(db: Session, url: str) -> models.Wallpaper:
    try:
        db.query(models.Wallpaper).filter(models.Wallpaper.url == url).update({models.Wallpaper.disabled: 1})
        db.commit()
        return db.query(models.Wallpaper).filter(models.Wallpaper.url == url).first()
    except Exception as e:
        db.rollback()
        raise e


def enable_wallpaper_with_url(db: Session, url: str) -> models.Wallpaper:
    try:
        db.query(models.Wallpaper).filter(models.Wallpaper.url == url).update({models.Wallpaper.disabled: 0})
        db.commit()
        return db.query(models.Wallpaper).filter(models.Wallpaper.url == url).first()
    except Exception as e:
        db.rollback()
        raise e


def get_all_fresh_wallpaper(db: Session) -> list[models.Wallpaper]:
    try:
        target_date = date.today() - timedelta(days=14)
        fresh_wallpapers = db.query(models.Wallpaper).filter(
            or_(
                models.Wallpaper.last_display_date < target_date,
                models.Wallpaper.last_display_date.is_(None)
            )
        ).all()

        # If no fresh wallpapers found, return all wallpapers
        if len(fresh_wallpapers) == 0:
            return db.query(models.Wallpaper).all()
        return fresh_wallpapers
    except Exception as e:
        db.rollback()
        raise e


def set_last_display_date_with_index(db: Session, index: int) -> models.Wallpaper:
    try:
        db.query(models.Wallpaper).filter(models.Wallpaper.id == index).update(
            {models.Wallpaper.last_display_date: date.today()})
        db.commit()
        return db.query(models.Wallpaper).filter(models.Wallpaper.id == index).first()
    except Exception as e:
        db.rollback()
        raise e


def reset_last_display(db: Session) -> bool:
    try:
        db.query(models.Wallpaper).update({models.Wallpaper.last_display_date: None})
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e


def add_avatar_strategy(db: Session, strategy: schemas.AvatarStrategy) -> schemas.AvatarStrategy:
    try:
        insert_stmt = insert(models.AvatarStrategy).values(**strategy.dict()).on_duplicate_key_update(
            mys_strategy_id=strategy.mys_strategy_id if strategy.mys_strategy_id is not None else models.AvatarStrategy.mys_strategy_id,
            hoyolab_strategy_id=strategy.hoyolab_strategy_id if strategy.hoyolab_strategy_id is not None else models.AvatarStrategy.hoyolab_strategy_id
        )
        db.execute(insert_stmt)
        db.commit()
        return strategy
    except Exception as e:
        db.rollback()
        raise e


"""
existing_strategy = db.query(models.AvatarStrategy).filter_by(avatar_id=strategy.avatar_id).first()

if existing_strategy:
if strategy.mys_strategy_id is not None:
    existing_strategy.mys_strategy_id = strategy.mys_strategy_id
if strategy.hoyolab_strategy_id is not None:
    existing_strategy.hoyolab_strategy_id = strategy.hoyolab_strategy_id
else:
new_strategy = models.AvatarStrategy(**strategy.dict())
db.add(new_strategy)

db.commit()
db.refresh(existing_strategy)
"""


def get_avatar_strategy_by_id(avatar_id: str, db: Session) -> models.AvatarStrategy:
    return db.query(models.AvatarStrategy).filter_by(avatar_id=avatar_id).first()


def get_all_avatar_strategy(db: Session) -> list[models.AvatarStrategy]:
    return db.query(models.AvatarStrategy).all()


def dump_daily_active_user_stats(db: Session, stats: schemas.DailyActiveUserStats) -> schemas.DailyActiveUserStats:
    try:
        db_stats = models.DailyActiveUserStats(**stats.dict())
        db.add(db_stats)
        db.commit()
        db.refresh(db_stats)
        return db_stats
    except Exception as e:
        db.rollback()
        raise e


def dump_daily_email_sent_stats(db: Session, stats: schemas.DailyEmailSentStats) -> schemas.DailyEmailSentStats:
    try:
        db_stats = models.DailyEmailSentStats(**stats.dict())
        db.add(db_stats)
        db.commit()
        db.refresh(db_stats)
        return db_stats
    except Exception as e:
        db.rollback()
        raise e
