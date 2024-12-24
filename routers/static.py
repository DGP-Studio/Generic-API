import logging
import httpx
import json
from redis import asyncio as redis
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from mysql_app.schemas import StandardResponse
from utils.authentication import verify_api_token
from base_logger import logger


class StaticUpdateURL(BaseModel):
    type: str
    url: str


china_router = APIRouter(tags=["Static"], prefix="/static")
global_router = APIRouter(tags=["Static"], prefix="/static")
fujian_router = APIRouter(tags=["Static"], prefix="/static")

CN_OSS_URL = "https://open-7419b310-fc97-4a0c-bedf-b8faca13eb7e-s3.saturn.xxyy.co:8443/hutao/{file_path}"


# @china_router.get("/zip/{file_path:path}")
async def cn_get_zipped_file(file_path: str, request: Request) -> RedirectResponse:
    """
    Endpoint used to redirect to the zipped static file in China server

    :param request: request object from FastAPI
    :param file_path: File relative path in Snap.Static.Zip

    :return: 302 Redirect to the zip file
    """
    # https://static-next.snapgenshin.com/d/zip/{file_path}
    quality = request.headers.get("x-hutao-quality", "high").lower()
    archive_type = request.headers.get("x-hutao-archive", "minimum").lower()

    if quality == "unknown" or archive_type == "unknown":
        raise HTTPException(status_code=418, detail="Invalid request")

    match archive_type:
        case "minimum":
            if file_path == "ItemIcon.zip" or file_path == "EmotionIcon.zip":
                file_path = file_path.replace(".zip", "-Minimum.zip")
        case "full":
            pass
        case _:
            raise HTTPException(status_code=404, detail="Invalid minimum package")

    match quality:
        case "high":
            file_path = file_path.replace(".zip", "-tiny.zip")
            file_path = "tiny-zip/" + file_path
        case "raw":
            file_path = "zip/" + file_path
        case _:
            raise HTTPException(status_code=404, detail="Invalid quality")
    logging.debug(f"Redirecting to {CN_OSS_URL.format(file_path=file_path)}")
    return RedirectResponse(CN_OSS_URL.format(file_path=file_path), status_code=302)


@china_router.get("/raw/{file_path:path}")
@fujian_router.get("/raw/{file_path:path}")
async def cn_get_raw_file(file_path: str, request: Request) -> RedirectResponse:
    """
    Endpoint used to redirect to the raw static file in China server

    :param request: request object from FastAPI
    :param file_path: Raw file relative path in Snap.Static


    :return: 302 Redirect to the raw file
    """
    quality = request.headers.get("x-hutao-quality", "high").lower()

    match quality:
        case "high":
            file_path = "tiny-raw/" + file_path
        case "raw":
            file_path = "raw/" + file_path
        case _:
            raise HTTPException(status_code=404, detail="Invalid quality")
    logging.debug(f"Redirecting to {CN_OSS_URL.format(file_path=file_path)}")
    return RedirectResponse(CN_OSS_URL.format(file_path=file_path), status_code=302)


@global_router.get("/zip/{file_path:path}")
@china_router.get("/zip/{file_path:path}")
@fujian_router.get("/zip/{file_path:path}")
async def global_get_zipped_file(file_path: str, request: Request) -> RedirectResponse:
    """
    Endpoint used to redirect to the zipped static file in Global server

    :param request: request object from FastAPI
    :param file_path: Relative path in Snap.Static.Zip

    :return: Redirect to the zip file
    """
    quality = request.headers.get("x-hutao-quality", "high").lower()
    archive_type = request.headers.get("x-hutao-archive", "minimum").lower()

    if quality == "unknown" or archive_type == "unknown":
        raise HTTPException(status_code=418, detail="Invalid request")

    match archive_type:
        case "minimum":
            if file_path == "ItemIcon.zip" or file_path == "EmotionIcon.zip":
                file_path = file_path.replace(".zip", "-Minimum.zip")
        case "full":
            pass
        case _:
            raise HTTPException(status_code=404, detail="Invalid minimum package")

    match quality:
        case "high":
            file_path = file_path.replace(".zip", "-tiny.zip")
            return RedirectResponse(f"https://static-tiny.snapgenshin.cn/zip/{file_path}", status_code=302)
        case "raw":
            return RedirectResponse(f"https://static-zip.snapgenshin.cn/{file_path}", status_code=302)
        case _:
            raise HTTPException(status_code=404, detail="Invalid quality")


@global_router.get("/raw/{file_path:path}")
async def global_get_raw_file(file_path: str, request: Request) -> RedirectResponse:
    """
    Endpoint used to redirect to the raw static file in Global server

    :param request: request object from FastAPI
    :param file_path: Relative path in Snap.Static

    :return: 302 Redirect to the raw file
    """
    quality = request.headers.get("x-hutao-quality", "high").lower()

    match quality:
        case "high":
            return RedirectResponse(f"https://static-tiny.snapgenshin.cn/raw/{file_path}", status_code=302)
        case "raw":
            return RedirectResponse(f"https://static.snapgenshin.cn/{file_path}", status_code=302)
        case _:
            raise HTTPException(status_code=404, detail="Invalid quality")


async def list_static_files_size(redis_client) -> dict:
    # Raw
    api_url = "https://static-next.snapgenshin.com/api/fs/list"
    payload = {
        "path": "/tx/zip",
        "password": "",
        "page": 1,
        "per_page": 0,
        "refresh": False
    }
    response = httpx.post(api_url, json=payload)
    if response.status_code == 200:
        data = response.json().get("data", []).get("content", [])
    else:
        raise RuntimeError(
            f"Failed to list static files, \nstatus code: {response.status_code}, \ncontent: {response.text}")
    raw_minimum = [f for f in data if f["name"] != "ItemIcon.zip" and f["name"] != "EmotionIcon.zip"]
    raw_full = [f for f in data if f["name"] != "ItemIcon-Minimum.zip" or f["name"] == "EmotionIcon-Minimum.zip"]
    raw_minimum_size = sum([f["size"] for f in raw_minimum])
    raw_full_size = sum([f["size"] for f in raw_full])

    # Tiny
    payload = {
        "path": "/tx/tiny-zip",
        "password": "",
        "page": 1,
        "per_page": 0,
        "refresh": False
    }
    response = httpx.post(api_url, json=payload)
    if response.status_code == 200:
        data = response.json().get("data", []).get("content", [])
    else:
        raise RuntimeError(
            f"Failed to list static files, \nstatus code: {response.status_code}, \ncontent: {response.text}")
    tiny_minimum = [f for f in data if f["name"] != "ItemIcon-tiny.zip" and f["name"] != "EmotionIcon-tiny.zip"]
    tiny_full = [f for f in data if
                 f["name"] != "ItemIcon-Minimum-tiny.zip" or f["name"] == "EmotionIcon-Minimum-tiny.zip"]
    tiny_minimum_size = sum([f["size"] for f in tiny_minimum])
    tiny_full_size = sum([f["size"] for f in tiny_full])
    zip_size_data = {
        "raw_minimum": raw_minimum_size,
        "raw_full": raw_full_size,
        "tiny_minimum": tiny_minimum_size,
        "tiny_full": tiny_full_size
    }
    await redis_client.set("static_files_size", json.dumps(zip_size_data), ex=60 * 60 * 3)
    logger.info(f"Updated static files size data: {zip_size_data}")
    return zip_size_data


@china_router.get("/size", response_model=StandardResponse)
@global_router.get("/size", response_model=StandardResponse)
@fujian_router.get("/size", response_model=StandardResponse)
async def get_static_files_size(request: Request) -> StandardResponse:
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    static_files_size = await redis_client.get("static_files_size")
    if static_files_size:
        static_files_size = json.loads(static_files_size)
    else:
        logger.info("Redis cache for static files size not found, fetching from API")
        static_files_size = await list_static_files_size(redis_client)
    response = StandardResponse(
        retcode=0,
        message="Success",
        data=static_files_size
    )
    return response


@china_router.get("/size/reset", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@global_router.get("/size/reset", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.get("/size/reset", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def reset_static_files_size(request: Request) -> StandardResponse:
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    new_data = await list_static_files_size(redis_client)
    response = StandardResponse(
        retcode=0,
        message="Success",
        data=new_data
    )
    return response
