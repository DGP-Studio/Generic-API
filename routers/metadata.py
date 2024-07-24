import json
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from utils.dgp_utils import validate_client_is_updated
from utils.redis_utils import redis_conn
from mysql_app.schemas import StandardResponse

china_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")
global_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")


def get_banned_files() -> dict:
    """
    Get the list of censored files.

    :return: a list of censored files
    """
    if redis_conn:
        metadata_censored_files = redis_conn.get("metadata_censored_files")
        if metadata_censored_files:
            return {
                "source": "redis",
                "data": json.loads(metadata_censored_files)
            }
        else:
            return {
                "source": "redis",
                "data": []
            }
    return {
        "source": "None",
        "data": []
    }


@china_router.get("/ban", response_model=StandardResponse)
@global_router.get("/ban", response_model=StandardResponse)
async def get_ban_files_endpoint() -> StandardResponse:
    """
    Get the list of censored files. [FastAPI Endpoint]

    :return: a list of censored files in StandardResponse format
    """
    return StandardResponse(data={"ban": get_banned_files()})


@china_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def china_metadata_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://jihulab.com/DGP-Studio/Snap.Metadata/-/raw/main/{file_path}"
    host_for_censored_files = f"https://metadata.snapgenshin.com/{file_path}"

    if file_path in get_banned_files():
        return RedirectResponse(host_for_censored_files, status_code=302)
    else:
        return RedirectResponse(host_for_normal_files, status_code=302)


@global_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def global_metadata_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://hutao-metadata-pages.snapgenshin.cn/{file_path}"

    return RedirectResponse(host_for_normal_files, status_code=302)
