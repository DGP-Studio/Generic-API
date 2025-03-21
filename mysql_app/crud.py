from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert
from sqlalchemy import or_
from datetime import date, timedelta
from . import models, schemas
from typing import cast


def get_all_wallpapers(db: Session) -> list[models.Wallpaper]:
    return cast(list[models.Wallpaper], db.query(models.Wallpaper).all())

def add_wallpaper(db: Session, wallpaper: schemas.Wallpaper) -> models.Wallpaper:
    wallpaper_exists = check_wallpaper_exists(db, wallpaper)
    if wallpaper_exists:
        return wallpaper_exists

    db_wallpaper = models.Wallpaper(**wallpaper.model_dump())
    db.add(db_wallpaper)
    db.commit()
    db.refresh(db_wallpaper)
    return db_wallpaper

def check_wallpaper_exists(db: Session, wallpaper: schemas.Wallpaper) -> models.Wallpaper | None:
    return db.query(models.Wallpaper).filter(models.Wallpaper.url == wallpaper.url).first()

def disable_wallpaper_with_url(db: Session, url: str) -> models.Wallpaper:
    db.query(models.Wallpaper).filter(models.Wallpaper.url == url).update(
        {models.Wallpaper.disabled: 1}
    )
    db.commit()
    result = db.query(models.Wallpaper).filter(models.Wallpaper.url == url).first()
    return cast(models.Wallpaper, result)

def enable_wallpaper_with_url(db: Session, url: str) -> models.Wallpaper:
    db.query(models.Wallpaper).filter(models.Wallpaper.url == url).update(
        {models.Wallpaper.disabled: 0}
    )
    db.commit()
    result = db.query(models.Wallpaper).filter(models.Wallpaper.url == url).first()
    return cast(models.Wallpaper, result)

def get_all_fresh_wallpaper(db: Session) -> list[models.Wallpaper]:
    target_date = date.today() - timedelta(days=14)
    fresh_wallpapers = db.query(models.Wallpaper).filter(
        or_(
            models.Wallpaper.last_display_date < target_date,
            models.Wallpaper.last_display_date.is_(None)
        )
    ).all()

    if not fresh_wallpapers:
        return cast(list[models.Wallpaper], db.query(models.Wallpaper).all())
    return cast(list[models.Wallpaper], fresh_wallpapers)

def set_last_display_date_with_index(db: Session, index: int) -> models.Wallpaper:
    db.query(models.Wallpaper).filter(models.Wallpaper.id == index).update(
        {models.Wallpaper.last_display_date: date.today()}
    )
    db.commit()
    result = db.query(models.Wallpaper).filter(models.Wallpaper.id == index).first()
    assert result is not None, "Wallpaper not found"
    return cast(models.Wallpaper, result)

def reset_last_display(db: Session) -> bool:
    result = db.query(models.Wallpaper).update(
        {models.Wallpaper.last_display_date: None}
    )
    db.commit()
    assert result is not None, "Wallpaper not found"
    return True

def add_avatar_strategy(db: Session, strategy: schemas.AvatarStrategy) -> schemas.AvatarStrategy:
    insert_stmt = insert(models.AvatarStrategy).values(**strategy.model_dump()).on_duplicate_key_update(
        mys_strategy_id=strategy.mys_strategy_id if strategy.mys_strategy_id is not None else models.AvatarStrategy.mys_strategy_id,
        hoyolab_strategy_id=strategy.hoyolab_strategy_id if strategy.hoyolab_strategy_id is not None else models.AvatarStrategy.hoyolab_strategy_id
    )
    db.execute(insert_stmt)
    db.commit()
    return strategy

def get_avatar_strategy_by_id(avatar_id: str, db: Session) -> models.AvatarStrategy | None:
    return db.query(models.AvatarStrategy).filter_by(avatar_id=avatar_id).first()

def get_all_avatar_strategy(db: Session) -> list[models.AvatarStrategy] | None:
    result = db.query(models.AvatarStrategy).all()
    return cast(list[models.AvatarStrategy], result) if result else None

def dump_daily_active_user_stats(db: Session, stats: schemas.DailyActiveUserStats) -> schemas.DailyActiveUserStats:
    db_stats = models.DailyActiveUserStats(**stats.model_dump())
    db.add(db_stats)
    db.commit()
    db.refresh(db_stats)
    return db_stats

def dump_daily_email_sent_stats(db: Session, stats: schemas.DailyEmailSentStats) -> schemas.DailyEmailSentStats:
    db_stats = models.DailyEmailSentStats(**stats.model_dump())
    db.add(db_stats)
    db.commit()
    db.refresh(db_stats)
    return db_stats