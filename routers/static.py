import os
import httpx
import json
import asyncio  # added asyncio import
import aiofiles
from redis import asyncio as aioredis
from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
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

    # For china and fujian: try to use real-time commit hash from Redis.
    if region in ("china", "fujian"):
        archive_quality = "original" if quality in ["original", "raw"] else "tiny"
        commit_key = f"commit:static-archive:{archive_quality}"
        commit_hash = await redis_client.get(commit_key)
        if commit_hash:
            commit_hash = commit_hash.decode("utf-8")
            real_key = f"static-cdn:{archive_quality}:{commit_hash}:{file_path.replace('.zip', '')}"
            real_url = await redis_client.get(real_key)
            if real_url:
                real_url = real_url.decode("utf-8")
                logger.debug(f"Redirecting to real-time zip URL: {real_url}")
                return RedirectResponse(real_url.format(file_path=file_path), status_code=301)

    # Fallback using template URL from Redis.
    if quality == "high":
        fallback_key = f"url:{region}:static:zip:tiny"
    elif quality in ("original", "raw"):
        fallback_key = f"url:{region}:static:zip:original"
    else:
        raise HTTPException(status_code=422, detail=f"{quality} is not a valid quality value")
    resource_endpoint = await redis_client.get(fallback_key)
    resource_endpoint = resource_endpoint.decode("utf-8")
    logger.debug(f"Redirecting to fallback template zip URL: {resource_endpoint.format(file_path=file_path)}")
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
    elif quality == "original" or quality == "raw":
        resource_endpoint = await redis_client.get(f"url:{region}:static:raw:original")
    else:
        raise HTTPException(status_code=422, detail=f"{quality} is not a valid quality value")
    resource_endpoint = resource_endpoint.decode("utf-8")

    logger.debug(f"Redirecting to {resource_endpoint.format(file_path=file_path)}")
    return RedirectResponse(resource_endpoint.format(file_path=file_path), status_code=301)


@china_router.get("/template", response_model=StandardResponse)
@global_router.get("/template", response_model=StandardResponse)
@fujian_router.get("/template", response_model=StandardResponse)
async def get_static_files_template(request: Request) -> StandardResponse:
    """
    Endpoint used to get the template URL for static files

    :param request: request object from FastAPI

    :return: 301 Redirect to the template URL
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    quality = request.headers.get("x-hutao-quality", "high").lower()
    if quality != "original":
        quality = "tiny"

    if request.url.path.startswith("/cn"):
        region = "china"
    elif request.url.path.startswith("/global"):
        region = "global"
    elif request.url.path.startswith("/fj"):
        region = "fujian"
    else:
        raise HTTPException(status_code=400, detail="Invalid router")
    try:
        zip_template = await redis_client.get(f"url:{region}:static:zip:{quality}")
        if zip_template is None:
            raise ValueError("Zip template URL not found in Redis")
        zip_template = zip_template.decode("utf-8")
        raw_template = await redis_client.get(f"url:{region}:static:raw:{quality}")
        if raw_template is None:
            raise ValueError("Raw template URL not found in Redis")
        raw_template = raw_template.decode("utf-8")
        zip_template = zip_template.replace("{file_path}", "{0}")
        raw_template = raw_template.replace("{file_path}", "{0}")
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to retrieve or decode template URL from Redis: {e}")
        raise HTTPException(status_code=500, detail="Template URL not found")

    return StandardResponse(
        data={
            "zip_template": zip_template,
            "raw_template": raw_template
        }
    )


async def list_static_files_size_by_alist(redis_client) -> dict:
    """
    List the size of static files using Alist API

    DEPRECATED: This function is deprecated and may be removed in the future.
    """

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
    original_meta_url = "https://static-archive.snapgenshin.cn/original/meta.json"
    tiny_meta_url = "https://static-archive.snapgenshin.cn/tiny/meta.json"
    original_size = httpx.get(original_file_size_json_url).json()
    tiny_size = httpx.get(tiny_file_size_json_url).json()
    original_meta = httpx.get(original_meta_url).json()
    tiny_meta = httpx.get(tiny_meta_url).json()

    # Calculate the total size for each category
    original_full = sum(item["size"] for item in original_size if "Minimum" not in item["name"])
    original_minimum = sum(
        item["size"] for item in original_size if item["name"] not in ["EmotionIcon.zip", "ItemIcon.zip"])
    tiny_full = sum(item["size"] for item in tiny_size if "Minimum" not in item["name"])
    tiny_minimum = sum(item["size"] for item in tiny_size if item["name"] not in ["EmotionIcon.zip", "ItemIcon.zip"])

    # Static Meta
    original_cache_time = original_meta["time"] # Format str - "05/06/2025 13:03:40"
    tiny_cache_time = tiny_meta["time"] # Format str - "05/06/2025 13:03:40"
    original_commit_hash = original_meta["commit"][:7]
    tiny_commit_hash = tiny_meta["commit"][:7]
    await redis_client.set(f"commit:static-archive:original", original_commit_hash)
    await redis_client.set(f"commit:static-archive:tiny", tiny_commit_hash)

    zip_size_data = {
        "original_minimum": original_minimum,
        "original_full": original_full,
        "tiny_minimum": tiny_minimum,
        "tiny_full": tiny_full,
        "original_cache_time": original_cache_time,
        "tiny_cache_time": tiny_cache_time,
        "original_commit_hash": original_commit_hash,
        "tiny_commit_hash": tiny_commit_hash
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


async def upload_all_static_archive_to_cdn(redis_client: aioredis.Redis):
    """
    Upload all static archive to CDN

    :param redis_client: Redis client
    :return: True if upload is successful, False otherwise
    """
    archive_type = ["original", "tiny"]
    upload_endpoint = f"https://{os.getenv('CDN_UPLOAD_HOSTNAME')}/api/upload?name="
    async with httpx.AsyncClient() as client:
        for archive_quality in archive_type:
            file_list_url = f"https://static-archive.snapgenshin.cn/{archive_quality}/file_info.json"
            meta_url = f"https://static-archive.snapgenshin.cn/{archive_quality}/meta.json"
            file_list = (await client.get(file_list_url)).json()
            meta = (await client.get(meta_url)).json()
            commit_hash = meta["commit"][:7]
            local_dir = f"./cache/static/{archive_quality}-{commit_hash}"
            os.makedirs(local_dir, exist_ok=True)
            for archive_file in file_list:
                file_name = archive_file["name"].replace(".zip", "")
                if await redis_client.exists(f"static-cdn:{archive_quality}:{commit_hash}:{file_name}"):
                    logger.info(f"File {archive_file['name']} already exists in CDN, skipping upload")
                    continue
                try:
                    file_url = f"https://static-archive.snapgenshin.cn/{archive_quality}/{archive_file['name']}"
                    # Download file asynchronously
                    response = await client.get(file_url)
                    local_file_path = f"{local_dir}/{archive_file['name']}"
                    async with aiofiles.open(local_file_path, "wb+") as f:
                        await f.write(response.content)
                    # Upload file to CDN with PUT method
                    async with aiofiles.open(local_file_path, "rb") as f:
                        file_data = await f.read()
                    upload_response = await client.put(upload_endpoint + archive_file['name'], data=file_data, timeout=180)
                    if upload_response.status_code != 200:
                        logger.error(f"Failed to upload {archive_file['name']} to CDN")
                    else:
                        resp_url = upload_response.text
                        if not resp_url.startswith("http"):
                            logger.error(f"Failed to upload {archive_file['name']} to CDN, response: {resp_url}")
                        else:
                            logger.info(f"Uploaded {archive_file['name']} to CDN, response: {resp_url}")
                            await redis_client.set(f"static-cdn:{archive_quality}:{commit_hash}:{file_name}", resp_url)
                except Exception as e:
                    logger.error(f"Failed to upload {archive_file['name']} to CDN, error: {e}")
                    continue
                finally:
                    # Offload local file removal to avoid blocking
                    await asyncio.to_thread(os.remove, local_file_path)


@china_router.post("/cdn/upload", dependencies=[Depends(verify_api_token)])
@global_router.post("/cdn/upload", dependencies=[Depends(verify_api_token)])
@fujian_router.post("/cdn/upload", dependencies=[Depends(verify_api_token)])
async def background_upload_to_cdn(request: Request, background_tasks: BackgroundTasks):
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    background_tasks.add_task(upload_all_static_archive_to_cdn, redis_client)
    return {"message": "Background CDN upload started."}


@china_router.get("/cdn/resources")
@global_router.get("/cdn/resources")
@fujian_router.get("/cdn/resources")
async def list_cdn_resources(request: Request):
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    keys = await redis_client.keys("static-cdn:*")
    resources = {}
    for key in keys:
        key_str = key.decode("utf-8")
        # key format: static-cdn:{archive_quality}:{commit_hash}:{file_name}
        parts = key_str.split(":")
        if len(parts) == 4:
            quality = parts[1]
            file_name = parts[3]
            url_val = await redis_client.get(key)
            if url_val:
                resources[f"{file_name}:{quality}"] = url_val.decode("utf-8")
    return resources