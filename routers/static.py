import logging
import httpx
import json
from redis import asyncio as aioredis
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from mysql_app.schemas import StandardResponse
from utils.authentication import verify_api_token
from base_logger import get_logger


class StaticUpdateURL(BaseModel):
    type: str
    url: str


logger = get_logger(__name__)
china_router = APIRouter(tags=["Static"], prefix="/static")
global_router = APIRouter(tags=["Static"], prefix="/static")
fujian_router = APIRouter(tags=["Static"], prefix="/static")


@china_router.get("/zip/{file_path:path}")
@global_router.get("/zip/{file_path:path}")
@fujian_router.get("/zip/{file_path:path}")
async def get_zip_resource(file_path: str, request: Request) -> RedirectResponse:
    """
    Endpoint used to redirect to the zipped static file

    :param request: request object from FastAPI

    :param file_path: File relative path in Snap.Static.Zip

    :return: 301 Redirect to the zip file
    """
    req_path = request.url.path
    if req_path.startswith("/cn"):
        region = "china"
    elif req_path.startswith("/global"):
        region = "global"
    elif req_path.startswith("/fj"):
        region = "fujian"
    else:
        raise HTTPException(status_code=400, detail="Invalid router")
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    quality = request.headers.get("x-hutao-quality", "high").lower()  # high/original
    archive_type = request.headers.get("x-hutao-archive", "minimum").lower()  # minimum/full

    if archive_type == "minimum":
        if file_path == "ItemIcon.zip" or file_path == "EmotionIcon.zip":
            file_path = file_path.replace(".zip", "-Minimum.zip")

    if quality == "high":
        resource_endpoint = await redis_client.get(f"url:{region}:static:zip:tiny")
    elif quality == "original":
        resource_endpoint = await redis_client.get(f"url:{region}:static:zip:original")
    else:
        raise HTTPException(status_code=422, detail=f"{quality} is not a valid quality value")
    resource_endpoint = resource_endpoint.decode("utf-8")

    logging.debug(f"Redirecting to {resource_endpoint.format(file_path=file_path)}")
    return RedirectResponse(resource_endpoint.format(file_path=file_path), status_code=301)


@china_router.get("/raw/{file_path:path}")
@global_router.get("/raw/{file_path:path}")
@fujian_router.get("/raw/{file_path:path}")
async def get_raw_resource(file_path: str, request: Request) -> RedirectResponse:
    """
    Endpoint used to redirect to the raw static file

    :param request: request object from FastAPI

    :param file_path: Raw file relative path in Snap.Static

    :return: 301 Redirect to the raw file
    """
    req_path = request.url.path
    if req_path.startswith("/cn"):
        region = "china"
    elif req_path.startswith("/global"):
        region = "global"
    elif req_path.startswith("/fj"):
        region = "fujian"
    else:
        raise HTTPException(status_code=400, detail="Invalid router")

    quality = request.headers.get("x-hutao-quality", "high").lower()
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    if quality == "high":
        resource_endpoint = await redis_client.get(f"url:{region}:static:raw:tiny")
    elif quality == "original":
        resource_endpoint = await redis_client.get(f"url:{region}:static:raw:original")
    else:
        raise HTTPException(status_code=422, detail=f"{quality} is not a valid quality value")
    resource_endpoint = resource_endpoint.decode("utf-8")

    logging.debug(f"Redirecting to {resource_endpoint.format(file_path=file_path)}")
    return RedirectResponse(resource_endpoint.format(file_path=file_path), status_code=301)


async def list_static_files_size_by_alist(redis_client) -> dict:
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
        "original_minimum": raw_minimum_size,
        "original_full": raw_full_size,
        "tiny_minimum": tiny_minimum_size,
        "tiny_full": tiny_full_size
    }
    await redis_client.set("static_files_size", json.dumps(zip_size_data), ex=60 * 60 * 3)
    logger.info(f"Updated static files size data via Alist API: {zip_size_data}")
    return zip_size_data


async def list_static_files_size_by_archive_json(redis_client) -> dict:
    original_file_size_json_url = "https://static-archive.snapgenshin.cn/original/file_info.json"
    tiny_file_size_json_url = "https://static-archive.snapgenshin.cn/tiny/file_info.json"
    original_size = httpx.get(original_file_size_json_url).json()
    tiny_size = httpx.get(tiny_file_size_json_url).json()

    # Calculate the total size for each category
    original_full = sum(item["size"] for item in original_size if "Minimum" not in item["name"])
    original_minimum = sum(
        item["size"] for item in original_size if item["name"] not in ["EmotionIcon.zip", "ItemIcon.zip"])
    tiny_full = sum(item["size"] for item in tiny_size if "Minimum" not in item["name"])
    tiny_minimum = sum(item["size"] for item in tiny_size if item["name"] not in ["EmotionIcon.zip", "ItemIcon.zip"])
    zip_size_data = {
        "original_minimum": original_minimum,
        "original_full": original_full,
        "tiny_minimum": tiny_minimum,
        "tiny_full": tiny_full
    }
    await redis_client.set("static_files_size", json.dumps(zip_size_data), ex=60 * 60 * 3)
    logger.info(f"Updated static files size data via Static Archive Json: {zip_size_data}")
    return zip_size_data


@china_router.get("/size", response_model=StandardResponse)
@global_router.get("/size", response_model=StandardResponse)
@fujian_router.get("/size", response_model=StandardResponse)
async def get_static_files_size(request: Request) -> StandardResponse:
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    static_files_size = await redis_client.get("static_files_size")
    if static_files_size:
        static_files_size = json.loads(static_files_size)
    else:
        logger.info("Redis cache for static files size not found, refreshing data")
        static_files_size = await list_static_files_size_by_archive_json(redis_client)
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
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    new_data = await list_static_files_size_by_archive_json(redis_client)
    response = StandardResponse(
        retcode=0,
        message="Success",
        data=new_data
    )
    return response
