import json
from datetime import date
from fastapi import APIRouter, Depends, Request
from utils.dgp_utils import validate_client_is_updated
from mysql_app import crud, models, schemas
from mysql_app.database import SessionLocal, engine
from mysql_app.schemas import Wallpaper, StandardResponse
from base_logger import logging
from utils.authentication import verify_api_token
from base_logger import logger
import random
import httpx
import os
import redis


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


today_wallpaper = None
if os.getenv("NO_REDIS", "false").lower() == "true":
    logger.info("Skipping Redis connection in Wallpaper module as NO_REDIS is set to true")
    redis_conn = None
else:
    redis_conn = redis.Redis(host="redis", port=6379, db=1, decode_responses=True)
router = APIRouter(tags=["category:wallpaper"])


@router.get("/cn/wallpaper/all", response_model=list[schemas.Wallpaper], dependencies=[Depends(verify_api_token)])
@router.get("/global/wallpaper/all", response_model=list[schemas.Wallpaper], dependencies=[Depends(verify_api_token)])
async def get_all_wallpapers(db: SessionLocal = Depends(get_db)):
    return crud.get_all_wallpapers(db)


@router.post("/cn/wallpaper/add", response_model=schemas.Wallpaper, dependencies=[Depends(verify_api_token)])
@router.post("/global/wallpaper/add", response_model=schemas.Wallpaper, dependencies=[Depends(verify_api_token)])
async def add_wallpaper(wallpaper: schemas.Wallpaper, db: SessionLocal = Depends(get_db)):
    wallpaper.display_date = None
    wallpaper.last_display_date = None
    wallpaper.disabled = False
    return crud.add_wallpaper(db, wallpaper)


@router.post("/cn/wallpaper/disable", dependencies=[Depends(verify_api_token)])
@router.post("/global/wallpaper/disable", dependencies=[Depends(verify_api_token)])
async def disable_wallpaper_with_url(request: Request, db: SessionLocal = Depends(get_db)):
    data = await request.json()
    url = data.get("url", "")
    if not url:
        return False
    return crud.disable_wallpaper_with_url(db, url)


@router.post("/cn/wallpaper/enable", dependencies=[Depends(verify_api_token)])
@router.post("/global/wallpaper/enable", dependencies=[Depends(verify_api_token)])
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
    logging.info("Picking a new wallpaper...")
    all_new_wallpapers = crud.get_all_fresh_wallpaper(db)
    today_wallpaper_pool = [wall for wall in all_new_wallpapers if wall.display_date == date.today()]
    if today_wallpaper_pool:
        wallpaper_pool = today_wallpaper_pool
    else:
        wallpaper_pool = all_new_wallpapers
    random_index = random.randint(0, len(wallpaper_pool) - 1)
    today_wallpaper = wallpaper_pool[random_index]
    res = crud.set_last_display_date_with_index(db, today_wallpaper.id)
    logging.info(f"Set last display date with index {today_wallpaper.id}: {res}")
    return today_wallpaper


@router.get("/cn/wallpaper/today", response_model=StandardResponse, dependencies=[Depends(validate_client_is_updated)])
@router.get("/global/wallpaper/today", response_model=StandardResponse, dependencies=[Depends(validate_client_is_updated)])
async def get_today_wallpaper(db: SessionLocal = Depends(get_db)):
    wallpaper = random_pick_wallpaper(db, False)
    response = StandardResponse()
    response.retcode = 0
    response.message = "ok"
    response.data = {
        "url": wallpaper.url,
        "source_url": wallpaper.source_url,
        "author": wallpaper.author,
        "uploader": wallpaper.uploader
    }
    return response


@router.get("/cn/wallpaper/refresh", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@router.get("/global/wallpaper/refresh", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def get_today_wallpaper(db: SessionLocal = Depends(get_db)):
    wallpaper = random_pick_wallpaper(db, False)
    response = StandardResponse()
    response.retcode = 0
    response.message = "Wallpaper refreshed"
    response.data = {
        "url": wallpaper.url,
        "source_url": wallpaper.source_url,
        "author": wallpaper.author,
        "uploader": wallpaper.uploader
    }
    return response


@router.get("/cn/wallpaper/reset", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@router.get("/global/wallpaper/reset", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def reset_last_display(db: SessionLocal = Depends(get_db)):
    response = StandardResponse()
    response.data = {
        "result": crud.reset_last_display(db)
    }
    return response


@router.get("/cn/wallpaper/bing", response_model=StandardResponse, dependencies=[Depends(validate_client_is_updated)])
@router.get("/global/wallpaper/bing", response_model=StandardResponse, dependencies=[Depends(validate_client_is_updated)])
async def get_bing_wallpaper(request: Request):
    # For test only
    url = request.url
    base_url = request
    url_hostname = request.url.hostname
    url_path = request.url.path
    base_url_hostname = request.base_url.hostname
    base_url_path = request.base_url.path
    logger.info(f"url: {url}, base_url: {base_url}, url_hostname: {url_hostname}, url_path: {url_path}, "
                f"base_url_hostname: {base_url_hostname}, base_url_path: {base_url_path}")
    # End of test

    if redis_conn is not None:
        redis_data = redis_conn.get("bing_wallpaper")
        if redis_data is not None:
            response = StandardResponse()
            response.message = "cached"
            response.data = redis_data
            return response
    # Get Bing wallpaper
    url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US"
    bing_output = httpx.get(url).json()
    data = {
        "url": f"https://www.bing.com{bing_output['images'][0]['url']}",
        "source_url": f"{bing_output['images'][0]['copyrightlink']}",
        "author": bing_output['images'][0]['copyright'],
        "uploader": "Microsoft Bing"
    }
    if redis_conn is not None:
        await redis_conn.set("bing_wallpaper", json.dumps(data), ex=3600)
    response = StandardResponse()
    response.message = "sourced"
    response.data = data
    return response
