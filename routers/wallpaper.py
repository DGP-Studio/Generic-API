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
from pydantic import BaseModel
import random
import httpx
import os
import redis


class WallpaperURL(BaseModel):
    url: str


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
    logger.info("Redis connection established in Wallpaper module")
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
@router.get("/global/wallpaper/today", response_model=StandardResponse,
            dependencies=[Depends(validate_client_is_updated)])
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
@router.get("/global/wallpaper/bing", response_model=StandardResponse,
            dependencies=[Depends(validate_client_is_updated)])
async def get_bing_wallpaper(request: Request):
    url_path = request.url.path
    if url_path.startswith("/global"):
        redis_key = "bing_wallpaper_global"
        bing_api = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US"
        bing_prefix = "www"
    elif url_path.startswith("/cn"):
        redis_key = "bing_wallpaper_cn"
        bing_api = "https://cn.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1"
        bing_prefix = "cn"
    else:
        redis_key = "bing_wallpaper_global"
        bing_api = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US"
        bing_prefix = "www"

    if redis_conn is not None:
        try:
            redis_data = json.loads(redis_conn.get(redis_key))
        except (json.JSONDecodeError, TypeError):
            redis_data = None
        if redis_data is not None:
            response = StandardResponse()
            response.message = f"cached: {redis_key}"
            response.data = redis_data
            return response
    # Get Bing wallpaper
    bing_output = httpx.get(bing_api).json()
    data = {
        "url": f"https://{bing_prefix}.bing.com{bing_output['images'][0]['url']}",
        "source_url": {bing_output['images'][0]['copyrightlink']},
        "author": bing_output['images'][0]['copyright'],
        "uploader": "Microsoft Bing"
    }
    if redis_conn is not None:
        res = redis_conn.set(redis_key, json.dumps(data), ex=3600)
        logger.info(f"Set bing_wallpaper to Redis result: {res}")
    response = StandardResponse()
    response.message = f"sourced: {redis_key}"
    response.data = data
    return response


@router.get("/cn/wallpaper/genshin-launcher", response_model=StandardResponse,
            dependencies=[Depends(validate_client_is_updated)])
@router.get("/global/wallpaper/genshin-launcher", response_model=StandardResponse,
            dependencies=[Depends(validate_client_is_updated)])
async def get_genshin_launcher_wallpaper(request: Request, language: str = "en-us"):
    language_set = ["zh-cn", "zh-tw", "en-us", "ja-jp", "ko-kr", "fr-fr", "de-de", "es-es", "pt-pt", "ru-ru", "id-id",
                    "vi-vn", "th-th"]
    url_path = request.url.path
    if url_path.startswith("/global"):
        if language not in language_set:
            language = "en-us"
        g_type = "global"
        redis_key = f"genshin_launcher_wallpaper_global_{language}"
        genshin_launcher_wallpaper_api = (f"https://sdk-os-static.mihoyo.com/hk4e_global/mdk/launcher/api/content"
                                          f"?filter_adv=true&key=gcStgarh&language={language}&launcher_id=10")
    elif url_path.startswith("/cn"):
        g_type = "cn"
        redis_key = "genshin_launcher_wallpaper_cn"
        genshin_launcher_wallpaper_api = (f"https://sdk-static.mihoyo.com/hk4e_cn/mdk/launcher/api/content?filter_adv"
                                          f"=true&key=eYd89JmJ&language=zh-cn&launcher_id=18")
    else:
        if language not in language_set:
            language = "en-us"
        g_type = "global"
        redis_key = f"genshin_launcher_wallpaper_global_{language}"
        genshin_launcher_wallpaper_api = (f"https://sdk-os-static.mihoyo.com/hk4e_global/mdk/launcher/api/content"
                                          f"?filter_adv=true&key=gcStgarh&language={language}&launcher_id=10")
    # Check Redis
    if redis_conn is not None:
        try:
            redis_data = json.loads(redis_conn.get(redis_key))
        except (json.JSONDecodeError, TypeError):
            redis_data = None
        if redis_data is not None:
            response = StandardResponse()
            response.message = f"cached: {redis_key}"
            response.data = redis_data
            return response
    # Get Genshin Launcher wallpaper from API
    genshin_output = httpx.get(genshin_launcher_wallpaper_api).json()
    background_url = genshin_output["data"]["adv"]["background"]
    data = {
        "url": background_url,
        "source_url": "https://mihoyo.com" if g_type == "cn" else "https://hoyoverse.com",
        "author": "miHoYo" if g_type == "cn" else "HoYoverse",
        "uploader": "miHoYo" if g_type == "cn" else "HoYoverse"
    }
    if redis_conn is not None:
        res = redis_conn.set(redis_key, json.dumps(data), ex=3600)
        logger.info(f"Set genshin_launcher_wallpaper to Redis result: {res}")
    response = StandardResponse()
    response.message = f"sourced: {redis_key}"
    response.data = data
    return response
