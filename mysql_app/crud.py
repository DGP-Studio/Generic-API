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


def get_all_git_repositories(db: Session, region: str | None = None) -> list[models.GitRepository]:
    """
    Get all git repositories from database, optionally filtered by region.
    
    :param db: Database session
    :param region: Optional region filter. If provided, only repositories in that region are returned.
                   If None, all repositories across all regions are returned.
    :return: List of GitRepository objects
    """
    query = db.query(models.GitRepository)
    if region:
        query = query.filter(models.GitRepository.region == region)
    return cast(list[models.GitRepository], query.all())


def get_git_repository_by_id(db: Session, repo_id: int) -> models.GitRepository | None:
    """Get a git repository by ID"""
    return db.query(models.GitRepository).filter(models.GitRepository.id == repo_id).first()


def get_git_repository_by_name(db: Session, name: str, region: str | None = None) -> models.GitRepository | None:
    """
    Get a git repository by name, optionally filtered by region.
    
    :param db: Database session
    :param name: Repository name to search for
    :param region: Optional region filter. If provided, searches for the repository in that region.
                   If None, returns the first repository with the given name (behavior depends on database order).
                   It's recommended to always provide a region when querying by name.
    :return: GitRepository object or None
    """
    query = db.query(models.GitRepository).filter(models.GitRepository.name == name)
    if region:
        query = query.filter(models.GitRepository.region == region)
    return query.first()


def create_git_repository(db: Session, repository: schemas.GitRepositoryCreate) -> models.GitRepository:
    """Create a new git repository record"""
    db_repository = models.GitRepository(**repository.model_dump())
    db.add(db_repository)
    db.commit()
    db.refresh(db_repository)
    return db_repository


def _apply_update_to_repository(db: Session, db_repository: models.GitRepository, repository: schemas.GitRepositoryUpdate) -> models.GitRepository:
    """Helper function to apply updates to a git repository"""
    update_data = repository.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_repository, key, value)
    
    db.commit()
    db.refresh(db_repository)
    return db_repository


def update_git_repository(db: Session, repo_id: int, repository: schemas.GitRepositoryUpdate) -> models.GitRepository | None:
    """Update a git repository by ID"""
    db_repository = db.query(models.GitRepository).filter(models.GitRepository.id == repo_id).first()
    if not db_repository:
        return None
    
    return _apply_update_to_repository(db, db_repository, repository)


def update_git_repository_by_name(db: Session, name: str, region: str, repository: schemas.GitRepositoryUpdate) -> models.GitRepository | None:
    """
    Update a git repository by name and region.
    
    :param db: Database session
    :param name: Repository name to search for
    :param region: Required region to identify the specific repository (since same name can exist in multiple regions)
    :param repository: Update data
    :return: Updated GitRepository object or None if not found
    """
    db_repository = db.query(models.GitRepository).filter(
        models.GitRepository.name == name,
        models.GitRepository.region == region
    ).first()
    if not db_repository:
        return None
    
    return _apply_update_to_repository(db, db_repository, repository)


def delete_git_repository(db: Session, repo_id: int) -> bool:
    """Delete a git repository by ID"""
    db_repository = db.query(models.GitRepository).filter(models.GitRepository.id == repo_id).first()
    if not db_repository:
        return False
    
    db.delete(db_repository)
    db.commit()
    return True


def delete_git_repository_by_name(db: Session, name: str, region: str) -> bool:
    """
    Delete a git repository by name and region.
    
    :param db: Database session
    :param name: Repository name to search for
    :param region: Required region to identify the specific repository (since same name can exist in multiple regions)
    :return: True if deleted successfully, False if not found
    """
    db_repository = db.query(models.GitRepository).filter(
        models.GitRepository.name == name,
        models.GitRepository.region == region
    ).first()
    if not db_repository:
        return False
    
    db.delete(db_repository)
    db.commit()
    return True