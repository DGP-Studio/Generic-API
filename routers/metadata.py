import os
import redis
import json
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from fastapi_utils.tasks import repeat_every
from utils.dgp_utils import validate_client_is_updated
from base_logger import logger


scan_duration = int(os.getenv("CENSOR_FILE_SCAN_DURATION", 30)) / 2  # half of the duration
metadata_censored_files = []

router = APIRouter(tags=["category:metadata"], dependencies=[Depends(validate_client_is_updated)])


@repeat_every(seconds=60 * scan_duration)
@router.on_event("startup")
async def refresh_metadata_censored_files():
    """
    Refresh metadata_censored_files every 30 minutes.
    """
    if os.getenv("NO_REDIS", "false").lower() == "true":
        logger.info("Skipping scheduled refreshing metadata_censored_files as NO_REDIS is set to true")
        return True
    logger.info(f"Start {scan_duration * 60}-min scheduled refreshing metadata_censored_files")
    global metadata_censored_files
    if os.getenv("NO_REDIS", "false").lower() == "true":
        logger.info("Skipping Redis connection in Wallpaper module as NO_REDIS is set to true")
        r = None
    else:
        REDIS_HOST = os.getenv("REDIS_HOST", "redis")
        logger.info(f"Connecting to Redis at {REDIS_HOST}")
        r = redis.Redis(host=REDIS_HOST, port=6379, db=1, decode_responses=True)
        logger.info("Redis connection established")
    redis_data = r.get("metadata_censored_files")
    logger.info(f"Receive data of metadata_censored_files from Redis: {redis_data}")
    if redis_data is not None:
        metadata_censored_files = json.loads(redis_data)
    else:
        metadata_censored_files = []
    r.close()
    logger.info(f"Redis connection closed as scheduled refreshing metadata_censored_files finished")


@router.get("/cn/ban")
@router.get("/global/ban")
async def get_banned_files():
    global metadata_censored_files
    return metadata_censored_files


@router.get("/cn/metadata/{file_path:path}", tags=["region:cn"])
async def china_metadata_request_handler(file_path: str):
    """
    Handle requests to metadata files.
    :param file_path: Path to the metadata file
    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://jihulab.com/DGP-Studio/Snap.Metadata/-/raw/main/{file_path}"
    host_for_censored_files = f"https://metadata.snapgenshin.com/{file_path}"

    if file_path in metadata_censored_files:
        return RedirectResponse(host_for_censored_files, status_code=302)
    else:
        return RedirectResponse(host_for_normal_files, status_code=302)


@router.get("/global/metadata/{file_path:path}", tags=["region:global"])
async def global_metadata_request_handler(file_path: str):
    """
    Handle requests to metadata files.
    :param file_path: Path to the metadata file
    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://hutao-metadata-pages.snapgenshin.cn/{file_path}"

    return RedirectResponse(host_for_normal_files, status_code=302)
