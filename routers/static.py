import logging

from fastapi import APIRouter, Depends, Response, Request, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from mysql_app import schemas
from mysql_app.schemas import StandardResponse
from utils.authentication import verify_api_token


class StaticUpdateURL(BaseModel):
    type: str
    url: str


china_router = APIRouter(tags=["Static"], prefix="/static")
global_router = APIRouter(tags=["Static"], prefix="/static")

CN_OSS_URL = "https://static-next.snapgenshin.com/d/tx/{file_path}"


@china_router.get("/zip/{file_path:path}")
async def cn_get_zipped_file(file_path: str, request: Request):
    """
    Endpoint used to redirect to the zipped static file in China server

    :param request: request object from FastAPI
    :param file_path: File relative path in Snap.Static.Zip

    :return: 302 Redirect to the zip file
    """
    # https://jihulab.com/DGP-Studio/Snap.Static.Zip/-/raw/main/{file_path}
    # https://static-next.snapgenshin.com/d/zip/{file_path}
    quality = request.headers.get("x-quality", "raw").lower()
    minimum_package = request.headers.get("x-minimum", "true").lower()

    if quality == "unknown" or minimum_package == "unknown":
        raise HTTPException(status_code=418, detail="Invalid request")

    match minimum_package:
        case "true":
            if file_path == "ItemIcon.zip" or file_path == "EmotionIcon.zip":
                file_path = file_path.replace(".zip", "-Minimum.zip")
        case "false":
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
async def cn_get_raw_file(file_path: str, request: Request):
    """
    Endpoint used to redirect to the raw static file in China server

    :param request: request object from FastAPI
    :param file_path: Raw file relative path in Snap.Static


    :return: 302 Redirect to the raw file
    """
    quality = request.headers.get("x-quality", "raw").lower()

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
async def global_get_zipped_file(file_path: str, request: Request):
    """
    Endpoint used to redirect to the zipped static file in Global server

    :param request: request object from FastAPI
    :param file_path: Relative path in Snap.Static.Zip

    :return: Redirect to the zip file
    """
    quality = request.headers.get("x-quality", "raw").lower()
    minimum_package = request.headers.get("x-minimum", "true").lower()

    if quality == "unknown" or minimum_package == "unknown":
        raise HTTPException(status_code=418, detail="Invalid request")

    match minimum_package:
        case "true":
            if file_path == "ItemIcon.zip" or file_path == "EmotionIcon.zip":
                file_path = file_path.replace(".zip", "-Minimum.zip")
        case "false":
            pass
        case _:
            raise HTTPException(status_code=404, detail="Invalid minimum package")

    match quality:
        case "high":
            file_path = file_path.replace(".zip", "-tiny.zip")
            logging.debug(f"Redirecting to https://static-tiny-zip.snapgenshin.cn/{file_path}")
            return RedirectResponse(f"https://static-tiny-zip.snapgenshin.cn/{file_path}", status_code=302)
        case "raw":
            logging.debug(f"Redirecting to https://static-zip.snapgenshin.cn/{file_path}")
            return RedirectResponse(f"https://static-zip.snapgenshin.cn/{file_path}", status_code=302)
        case _:
            raise HTTPException(status_code=404, detail="Invalid quality")


@global_router.get("/raw/{file_path:path}")
async def global_get_raw_file(file_path: str, request: Request):
    """
    Endpoint used to redirect to the raw static file in Global server

    :param request: request object from FastAPI
    :param file_path: Relative path in Snap.Static

    :return: 302 Redirect to the raw file
    """
    quality = request.headers.get("x-quality", "raw").lower()

    match quality:
        case "high":
            return RedirectResponse(f"https://static-tiny.snapgenshin.cn/{file_path}", status_code=302)
        case "raw":
            return RedirectResponse(f"https://static.snapgenshin.cn/{file_path}", status_code=302)
        case _:
            raise HTTPException(status_code=404, detail="Invalid quality")
