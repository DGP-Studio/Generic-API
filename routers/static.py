from fastapi import APIRouter
from fastapi.responses import RedirectResponse


china_router = APIRouter(tags=["Static"], prefix="/static")
global_router = APIRouter(tags=["Static"], prefix="/static")


@china_router.get("/zip/{file_path:path}")
async def cn_get_zipped_file(file_path: str):
    """
    Endpoint used to redirect to the zipped static file in China server

    :param file_path: File relative path in Snap.Static.Zip

    :return: 302 Redirect to the zip file
    """
    # https://jihulab.com/DGP-Studio/Snap.Static.Zip/-/raw/main/{file_path}
    # https://static-next.snapgenshin.com/d/zip/{file_path}
    return RedirectResponse(f"https://static-next.snapgenshin.com/d/zip/{file_path}", status_code=302)


@china_router.get("/raw/{file_path:path}")
async def cn_get_raw_file(file_path: str):
    """
    Endpoint used to redirect to the raw static file in China server

    :param file_path: Raw file relative path in Snap.Static

    :return: 302 Redirect to the raw file
    """
    # https://jihulab.com/DGP-Studio/Snap.Static/-/raw/main/{file_path}
    # https://static-next.snapgenshin.com/d/raw/{file_path}
    return RedirectResponse(f"https://jihulab.com/DGP-Studio/Snap.Static/-/raw/main/{file_path}", status_code=302)


@global_router.get("/zip/{file_path:path}")
async def global_get_zipped_file(file_path: str):
    """
    Endpoint used to redirect to the zipped static file in Global server

    :param file_path: Relative path in Snap.Static.Zip

    :return: Redirect to the zip file
    """
    return RedirectResponse(f"https://static-zip.snapgenshin.cn/{file_path}", status_code=302)


@global_router.get("/raw/{file_path:path}")
async def global_get_raw_file(file_path: str):
    """
    Endpoint used to redirect to the raw static file in Global server

    :param file_path: Relative path in Snap.Static

    :return: 302 Redirect to the raw file
    """
    return RedirectResponse(f"https://static.snapgenshin.cn/{file_path}", status_code=302)
