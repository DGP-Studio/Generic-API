import httpx
from fastapi import APIRouter, Response, status
from utils.dgp_utils import timely_update_allowed_ua

router = APIRouter(tags=["category:patch"])


def update_snap_hutao_latest_version():
    return httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao/releases/latest").json()["tag_name"] + ".0"


snap_hutao_latest_version = update_snap_hutao_latest_version()


@router.get("/cn/patch/hutao", tags=["region:cn"])
@router.get("/global/patch/hutao", tags=["region:global"])
async def generic_get_snap_hutao_latest_version():
    return {"version": snap_hutao_latest_version}


@router.patch("/cn/patch/hutao", tags=["region:cn"], include_in_schema=False)
@router.patch("/global/patch/hutao", tags=["region:global"], include_in_schema=False)
async def generic_patch_snap_hutao_latest_version(response: Response):
    global snap_hutao_latest_version
    snap_hutao_latest_version = update_snap_hutao_latest_version()
    timely_update_allowed_ua()
    response.status_code = status.HTTP_201_CREATED
    return {"version": snap_hutao_latest_version}

# Yae Patch API handled by https://github.com/Masterain98/SnapHutao-Yae-Patch-Backend
# @router.get("/cn/patch/yae") -> use Nginx reverse proxy instead
# @router.get("/global/patch/yae") -> use Nginx reverse proxy instead
