from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import date, timedelta
from . import models, schemas


def get_all_wallpapers(db: Session):
    return db.query(models.Wallpaper).all()


def add_wallpaper(db: Session, wallpaper: schemas.Wallpaper):
    # Check exists and add
    wallpaper_exists = check_wallpaper_exists(db, wallpaper)
    if wallpaper_exists:
        return wallpaper_exists
    db_wallpaper = models.Wallpaper(**wallpaper.dict())
    db.add(db_wallpaper)
    db.commit()
    db.refresh(db_wallpaper)
    return db_wallpaper


def check_wallpaper_exists(db: Session, wallpaper: schemas.Wallpaper):
    return db.query(models.Wallpaper).filter(models.Wallpaper.url == wallpaper.url).first()


def disable_wallpaper_with_url(db: Session, url: str):
    db.query(models.Wallpaper).filter(models.Wallpaper.url == url).update({models.Wallpaper.disabled: 1})
    db.commit()
    return True


def enable_wallpaper_with_url(db: Session, url: str):
    db.query(models.Wallpaper).filter(models.Wallpaper.url == url).update({models.Wallpaper.disabled: 0})
    db.commit()
    return True


def get_all_fresh_wallpaper(db: Session):
    target_date = str(date.today() - timedelta(days=3))
    result = db.query(models.Wallpaper).filter(or_(models.Wallpaper.last_display_date < target_date,
                                                   models.Wallpaper.last_display_date is None)).all()
    if result is None:
        return db.query(models.Wallpaper).all()[0]
    return result


def set_last_display_date_with_index(db: Session, index: int):
    db.query(models.Wallpaper).filter(models.Wallpaper.id == index).update(
        {models.Wallpaper.last_display_date: date.today()})
    db.commit()
    return True


def reset_last_display(db: Session):
    db.query(models.Wallpaper).update({models.Wallpaper.last_display_date: None})
    db.commit()
    return True
