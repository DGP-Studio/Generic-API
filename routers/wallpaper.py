from fastapi import APIRouter, Depends, Request
from utils.dgp_utils import validate_client_is_updated
from mysql_app import crud, models, schemas
from mysql_app.database import SessionLocal, engine
from mysql_app.schemas import Wallpaper
from base_logger import logging
from utils.authentication import verify_api_token
import random


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


today_wallpaper = None
router = APIRouter(prefix="/wallpaper", tags=["category:wallpaper"])


@router.get("/all", response_model=list[schemas.Wallpaper], dependencies=[Depends(verify_api_token)])
async def get_all_wallpapers(db: SessionLocal = Depends(get_db)):
    return crud.get_all_wallpapers(db)


@router.post("/add", response_model=schemas.Wallpaper, dependencies=[Depends(verify_api_token)])
async def add_wallpaper(wallpaper: schemas.Wallpaper, db: SessionLocal = Depends(get_db)):
    wallpaper.display_date = None
    wallpaper.last_display_date = None
    wallpaper.disabled = False
    return crud.add_wallpaper(db, wallpaper)


@router.post("/disable", dependencies=[Depends(verify_api_token)])
async def disable_wallpaper_with_url(request: Request, db: SessionLocal = Depends(get_db)):
    data = await request.json()
    url = data.get("url", "")
    if not url:
        return False
    return crud.disable_wallpaper_with_url(db, url)


@router.post("/enable", dependencies=[Depends(verify_api_token)])
async def enable_wallpaper_with_url(request: Request, db: SessionLocal = Depends(get_db)):
    data = await request.json()
    url = data.get("url", "")
    if not url:
        return False
    return crud.enable_wallpaper_with_url(db, url)


def random_pick_wallpaper(db, force_refresh: bool = False) -> Wallpaper:
    global today_wallpaper
    if today_wallpaper and not force_refresh:
        return today_wallpaper
    logging.info("Random pick wallpaper")
    all_new_wallpapers = crud.get_all_fresh_wallpaper(db)
    random_index = random.randint(0, len(all_new_wallpapers) - 1)
    today_wallpaper = all_new_wallpapers[random_index]
    res = crud.set_last_display_date_with_index(db, today_wallpaper.id)
    logging.info(f"Set last display date with index {today_wallpaper.id}: {res}")
    return today_wallpaper


@router.get("/today", response_model=schemas.Wallpaper, dependencies=[Depends(validate_client_is_updated)])
async def get_today_wallpaper(db: SessionLocal = Depends(get_db)):
    random_pick_wallpaper(db, False)
    return today_wallpaper


@router.get("/refresh", response_model=schemas.Wallpaper, dependencies=[Depends(verify_api_token)])
async def get_today_wallpaper(db: SessionLocal = Depends(get_db)):
    random_pick_wallpaper(db, True)
    return today_wallpaper


@router.get("/reset", response_model=bool, dependencies=[Depends(verify_api_token)])
async def reset_last_display(db: SessionLocal = Depends(get_db)):
    return crud.reset_last_display(db)
