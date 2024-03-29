from fastapi import APIRouter, Depends, Request
import pymysql
from pydantic import BaseModel
from utils.dgp_utils import validate_client_is_updated
from mysql_app import crud, models, schemas
from mysql_app.database import SessionLocal, engine
from mysql_app.schemas import Wallpaper, StandardResponse
from base_logger import logging
from utils.authentication import verify_api_token
from base_logger import logger
import json
from datetime import date
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
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    logger.info(f"Connecting to Redis at {REDIS_HOST} for Wallpaper module")
    redis_conn = redis.Redis(host=REDIS_HOST, port=6379, db=1, decode_responses=True)
    logger.info("Redis connection established for Wallpaper module")

china_router = APIRouter(tags=["wallpaper"], prefix="/wallpaper")
global_router = APIRouter(tags=["wallpaper"], prefix="/wallpaper")


@china_router.get("/all", response_model=list[schemas.Wallpaper], dependencies=[Depends(verify_api_token)],
                  tags=["admin"])
@global_router.get("/all", response_model=list[schemas.Wallpaper], dependencies=[Depends(verify_api_token)],
                   tags=["admin"])
async def get_all_wallpapers(db: SessionLocal = Depends(get_db)):
    """
    Get all wallpapers in database. **This endpoint requires API token verification**

    :param db: Database session

    :return: A list of wallpapers objects
    """
    return crud.get_all_wallpapers(db)


@china_router.post("/add", response_model=schemas.StandardResponse, dependencies=[Depends(verify_api_token)],
                   tags=["admin"])
@global_router.post("/add", response_model=schemas.StandardResponse, dependencies=[Depends(verify_api_token)],
                    tags=["admin"])
async def add_wallpaper(wallpaper: schemas.Wallpaper, db: SessionLocal = Depends(get_db)):
    """
    Add a new wallpaper to database. **This endpoint requires API token verification**

    :param wallpaper: Wallpaper object

    :param db: DB session

    :return: StandardResponse object
    """
    response = StandardResponse()
    wallpaper.display_date = None
    wallpaper.last_display_date = None
    wallpaper.disabled = False
    add_result = crud.add_wallpaper(db, wallpaper)
    if add_result:
        response.data = {
            "url": add_result.url,
            "display_date": add_result.display_date,
            "last_display_date": add_result.last_display_date,
            "source_url": add_result.source_url,
            "author": add_result.author,
            "uploader": add_result.uploader,
            "disabled": add_result.disabled
        }
    return response


@china_router.post("/disable", dependencies=[Depends(verify_api_token)], tags=["admin"])
@global_router.post("/disable", dependencies=[Depends(verify_api_token)], tags=["admin"])
async def disable_wallpaper_with_url(request: Request, db: SessionLocal = Depends(get_db)):
    """
    Disable a wallpaper with its URL, so it won't be picked by the random wallpaper picker.
    **This endpoint requires API token verification**

    :param request: Request object from FastAPI

    :param db: DB session

    :return: False if failed, Wallpaper object if successful
    """
    data = await request.json()
    url = data.get("url", "")
    if not url:
        return False
    return crud.disable_wallpaper_with_url(db, url)


@china_router.post("/enable", dependencies=[Depends(verify_api_token)], tags=["admin"])
@global_router.post("/enable", dependencies=[Depends(verify_api_token)], tags=["admin"])
async def enable_wallpaper_with_url(request: Request, db: SessionLocal = Depends(get_db)):
    """
    Enable a wallpaper with its URL, so it will be picked by the random wallpaper picker.
    **This endpoint requires API token verification**

    :param request: Request object from FastAPI

    :param db: DB session

    :return: false if failed, Wallpaper object if successful
    """
    data = await request.json()
    url = data.get("url", "")
    if not url:
        return False
    return crud.enable_wallpaper_with_url(db, url)


def random_pick_wallpaper(db, force_refresh: bool = False) -> Wallpaper:
    """
    Randomly pick a wallpaper from the database

    :param db: DB session
    :param force_refresh: True to force refresh the wallpaper, False to use the cached one
    :return: Wallpaper object
    """
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


@china_router.get("/today", response_model=StandardResponse)
@global_router.get("/today", response_model=StandardResponse)
async def get_today_wallpaper(db: SessionLocal = Depends(get_db)):
    """
    Get today's wallpaper

    :param db: DB session

    :return: StandardResponse object with wallpaper data in data field
    """
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


@china_router.get("/refresh", response_model=StandardResponse, dependencies=[Depends(verify_api_token)],
                  tags=["admin"])
@global_router.get("/refresh", response_model=StandardResponse, dependencies=[Depends(verify_api_token)],
                   tags=["admin"])
async def get_today_wallpaper(db: SessionLocal = Depends(get_db)):
    """
    Refresh today's wallpaper. **This endpoint requires API token verification**

    :param db: DB session

    :return: StandardResponse object with new wallpaper data in data field
    """
    while True:
        try:
            wallpaper = random_pick_wallpaper(db, True)
            response = StandardResponse()
            response.retcode = 0
            response.message = "Wallpaper refreshed"
            response.data = {
                "url": wallpaper.url,
                "source_url": wallpaper.source_url,
                "author": wallpaper.author,
                "uploader": wallpaper.uploader
            }
            break
        except pymysql.err.OperationalError:
            pass
    return response


@china_router.get("/reset", response_model=StandardResponse, dependencies=[Depends(verify_api_token)],
                  tags=["admin"])
@global_router.get("/reset", response_model=StandardResponse, dependencies=[Depends(verify_api_token)],
                   tags=["admin"])
async def reset_last_display(db: SessionLocal = Depends(get_db)):
    """
    Reset last display date of all wallpapers. **This endpoint requires API token verification**

    :param db: DB session

    :return: StandardResponse object with result in data field
    """
    response = StandardResponse()
    response.data = {
        "result": crud.reset_last_display(db)
    }
    return response


@china_router.get("/bing", response_model=StandardResponse)
@global_router.get("/bing", response_model=StandardResponse)
async def get_bing_wallpaper(request: Request):
    """
    Get Bing wallpaper

    :param request: Request object from FastAPI

    :return: StandardResponse object with Bing wallpaper data in data field
    """
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
            response = StandardResponse()
            response.message = f"cached: {redis_key}"
            response.data = redis_data
            return response
        except (json.JSONDecodeError, TypeError):
            pass
    # Get Bing wallpaper
    bing_output = httpx.get(bing_api).json()
    data = {
        "url": f"https://{bing_prefix}.bing.com{bing_output['images'][0]['url']}",
        "source_url": bing_output['images'][0]['copyrightlink'],
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


@china_router.get("/genshin-launcher", response_model=StandardResponse)
@global_router.get("/genshin-launcher", response_model=StandardResponse)
async def get_genshin_launcher_wallpaper(request: Request, language: str = "en-us"):
    """
    Get Genshin Impact launcher wallpaper

    :param request: Request object from FastAPI

    :param language: Target language

    :return: StandardResponse object with Genshin Impact launcher wallpaper data in data field
    """
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
