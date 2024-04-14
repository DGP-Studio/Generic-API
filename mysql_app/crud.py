from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import insert
from sqlalchemy import or_
from datetime import date, timedelta
from . import models, schemas


def get_all_wallpapers(db: Session) -> list[models.Wallpaper]:
    return db.query(models.Wallpaper).all()


def add_wallpaper(db: Session, wallpaper: schemas.Wallpaper) -> models.Wallpaper:
    # Check exists and add
    wallpaper_exists = check_wallpaper_exists(db, wallpaper)
    if wallpaper_exists:
        return wallpaper_exists
    db_wallpaper = models.Wallpaper(**wallpaper.dict())
    db.add(db_wallpaper)
    db.commit()
    db.refresh(db_wallpaper)
    return db_wallpaper


def check_wallpaper_exists(db: Session, wallpaper: schemas.Wallpaper) -> models.Wallpaper | None:
    return db.query(models.Wallpaper).filter(models.Wallpaper.url == wallpaper.url).first()


def disable_wallpaper_with_url(db: Session, url: str) -> models.Wallpaper:
    db.query(models.Wallpaper).filter(models.Wallpaper.url == url).update({models.Wallpaper.disabled: 1})
    db.commit()
    return db.query(models.Wallpaper).filter(models.Wallpaper.url == url).first()


def enable_wallpaper_with_url(db: Session, url: str) -> models.Wallpaper:
    db.query(models.Wallpaper).filter(models.Wallpaper.url == url).update({models.Wallpaper.disabled: 0})
    db.commit()
    return db.query(models.Wallpaper).filter(models.Wallpaper.url == url).first()


def get_all_fresh_wallpaper(db: Session) -> list[models.Wallpaper]:
    target_date = str(date.today() - timedelta(days=14))
    all_wallpapers = db.query(models.Wallpaper)
    fresh_wallpapers = all_wallpapers.filter(or_(models.Wallpaper.last_display_date < target_date,
                                                 models.Wallpaper.last_display_date == None)).all()
    if len(fresh_wallpapers) == 0:
        return db.query(models.Wallpaper).all()
    return fresh_wallpapers


def set_last_display_date_with_index(db: Session, index: int) -> models.Wallpaper:
    db.query(models.Wallpaper).filter(models.Wallpaper.id == index).update(
        {models.Wallpaper.last_display_date: date.today()})
    db.commit()
    return db.query(models.Wallpaper).filter(models.Wallpaper.id == index).first()


def reset_last_display(db: Session) -> bool:
    db.query(models.Wallpaper).update({models.Wallpaper.last_display_date: None})
    db.commit()
    return True


def add_avatar_strategy(db: Session, strategy: schemas.AvatarStrategy) -> schemas.AvatarStrategy:
    insert_stmt = insert(models.AvatarStrategy).values(**strategy.dict()).on_duplicate_key_update(
        mys_strategy_id=strategy.mys_strategy_id if strategy.mys_strategy_id is not None else models.AvatarStrategy.mys_strategy_id,
        hoyolab_strategy_id=strategy.hoyolab_strategy_id if strategy.hoyolab_strategy_id is not None else models.AvatarStrategy.hoyolab_strategy_id
    )
    db.execute(insert_stmt)
    db.commit()

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

    return strategy


def get_avatar_strategy_by_id(avatar_id: str, db: Session) -> models.AvatarStrategy:
    return db.query(models.AvatarStrategy).filter_by(avatar_id=avatar_id).first()


def get_all_avatar_strategy(db: Session) -> list[models.AvatarStrategy]:
    return db.query(models.AvatarStrategy).all()
