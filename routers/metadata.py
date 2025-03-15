from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from redis import asyncio as aioredis
from mysql_app.schemas import StandardResponse
from utils.dgp_utils import validate_client_is_updated
from base_logger import logger
import httpx
import os


china_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")
global_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")
fujian_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")


async def fetch_metadata_repo_file_list(redis_client: aioredis.Redis) -> None:
    api_endpoint = "https://api.github.com/repos/DGP-Studio/Snap.Metadata/git/trees/main?recursive=1"
    headers = {
        "Authorization": f"Bearer {os.getenv('GITHUB_PAT')}",
    }
    tree_data = httpx.get(api_endpoint, headers=headers).json()["tree"]
    tree_data = [file["path"] for file in tree_data if file["type"] == "blob" and file["path"].endswith(".json")]
    async with redis_client.pipeline() as pipe:
        for file in tree_data:
            file_language = file.split("/")[1].upper()
            sub_path = '/'.join(file.split("/")[2:])
            logger.info(f"Adding metadata file {sub_path} to metadata:{file_language}")
            await pipe.sadd(f"metadata:{file_language}", sub_path)
    await pipe.expire(f"metadata:{file_language}", 15 * 60)
    await pipe.execute()


@china_router.get("/list", dependencies=[Depends(validate_client_is_updated)])
@global_router.get("/list", dependencies=[Depends(validate_client_is_updated)])
@fujian_router.get("/list", dependencies=[Depends(validate_client_is_updated)])
async def metadata_list_handler(request: Request, lang: str) -> dict:
    """
    List all available metadata files.

    :param request: Request object

    :param lang: Language of the metadata files
    """
    lang = lang.upper()
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    if request.url.path.startswith("/cn"):
        metadata_endpoint = await redis_client.get("url:china:metadata")
    elif request.url.path.startswith("/global"):
        metadata_endpoint = await redis_client.get("url:global:metadata")
    elif request.url.path.startswith("/fj"):
        metadata_endpoint = await redis_client.get("url:fujian:metadata")
    else:
        raise HTTPException(status_code=400, detail="Invalid router")
    metadata_endpoint = metadata_endpoint.decode("utf-8")

    metadata_file_list = await redis_client.smembers(f"metadata:{lang}")
    if not metadata_file_list:
        await fetch_metadata_repo_file_list(redis_client)
        metadata_file_list = await redis_client.smembers(f"metadata:{lang}")
        logger.info(f"{len(metadata_file_list)} metadata files are available: {metadata_file_list}")
    if not metadata_file_list:
        raise HTTPException(status_code=404, detail="No metadata files found")
    metadata_file_list = [file.decode("utf-8") for file in metadata_file_list]
    download_links = [metadata_endpoint.format(file_path=file) for file in metadata_file_list]

    return StandardResponse(
        data=download_links
    )


@china_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def china_metadata_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param request: Request object

    :param file_path: Path to the metadata file

    :return: HTTP 301 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    china_metadata_endpoint = await redis_client.get("url:china:metadata")
    china_metadata_endpoint = china_metadata_endpoint.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(china_metadata_endpoint, status_code=301)


@global_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def global_metadata_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param request: Request object

    :param file_path: Path to the metadata file

    :return: HTTP 301 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    global_metadata_endpoint = await redis_client.get("url:global:metadata")
    global_metadata_endpoint = global_metadata_endpoint.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(global_metadata_endpoint, status_code=301)


@fujian_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def fujian_metadata_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param request: Request object

    :param file_path: Path to the metadata file

    :return: HTTP 301 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    fujian_metadata_endpoint = await redis_client.get("url:fujian:metadata")
    fujian_metadata_endpoint = fujian_metadata_endpoint.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(fujian_metadata_endpoint, status_code=301)
