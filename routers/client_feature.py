from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from redis import asyncio as aioredis


china_router = APIRouter(tags=["Client Feature"], prefix="/client")
global_router = APIRouter(tags=["Client Feature"], prefix="/client")
fujian_router = APIRouter(tags=["Client Feature"], prefix="/client")


@china_router.get("/{file_path:path}")
async def china_client_feature_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to client feature metadata files.

    :param request: Request object from FastAPI

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    host_for_normal_files = await redis_client.get("url:china:client-feature")
    host_for_normal_files = host_for_normal_files.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(host_for_normal_files, status_code=302)


@global_router.get("/{file_path:path}")
async def global_client_feature_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to client feature metadata files.

    :param request: Request object from FastAPI

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    host_for_normal_files = await redis_client.get("url:global:client-feature")
    host_for_normal_files = host_for_normal_files.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(host_for_normal_files, status_code=302)


@fujian_router.get("/{file_path:path}")
async def fujian_client_feature_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to client feature metadata files.

    :param request: Request object from FastAPI

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    host_for_normal_files = await redis_client.get("url:fujian:client-feature")
    host_for_normal_files = host_for_normal_files.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(host_for_normal_files, status_code=302)
