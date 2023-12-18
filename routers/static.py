from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from utils.dgp_utils import validate_client_is_updated


router = APIRouter(tags=["category:static"], dependencies=[Depends(validate_client_is_updated)])


@router.get("/cn/static/zip/{file_path:path}", tags=["region:cn"])
async def cn_get_zipped_file(file_path: str):
    # https://jihulab.com/DGP-Studio/Snap.Static.Zip/-/raw/main/{file_path}
    # https://static-next.snapgenshin.com/d/zip/{file_path}
    return RedirectResponse(f"https://jihulab.com/DGP-Studio/Snap.Static.Zip/-/raw/main/{file_path}", status_code=302)


@router.get("/cn/static/raw/{file_path:path}", tags=["region:cn"])
async def cn_get_raw_file(file_path: str):
    # https://jihulab.com/DGP-Studio/Snap.Static/-/raw/main/{file_path}
    # https://static-next.snapgenshin.com/d/raw/{file_path}
    return RedirectResponse(f"https://jihulab.com/DGP-Studio/Snap.Static/-/raw/main/{file_path}", status_code=302)


@router.get("/global/static/zip/{file_path:path}", tags=["region:global"])
async def global_get_zipped_file(file_path: str):
    return RedirectResponse(f"https://static-zip.snapgenshin.cn/{file_path}", status_code=302)


@router.get("/global/static/raw/{file_path:path}", tags=["region:global"])
async def global_get_raw_file(file_path: str):
    return RedirectResponse(f"https://static.snapgenshin.cn/{file_path}", status_code=302)
