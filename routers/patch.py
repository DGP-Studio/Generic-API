import httpx
from fastapi import APIRouter, Response, status
from fastapi.responses import RedirectResponse
from utils.dgp_utils import timely_update_allowed_ua
from config import github_headers

router = APIRouter(tags=["category:patch"])


def update_snap_hutao_latest_version() -> dict:
    github_meta = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao/releases/latest",
                            headers=github_headers).json()
    jihulab_meta = httpx.get(
        "https://jihulab.com/api/v4/projects/DGP-Studio%2FSnap.Hutao/releases/permalink/latest",
        follow_redirects=True).json()
    try:
        cn_version = jihulab_meta["tag_name"] + ".0"
        cn_url = list([a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                       if a["link_type"] == "package"])[0]
    except KeyError:
        cn_version = github_meta["tag_name"] + ".0"
        cn_url = github_meta["assets"][0]["browser_download_url"]
    except IndexError:
        cn_version = github_meta["tag_name"] + ".0"
        cn_url = github_meta["assets"][0]["browser_download_url"]

    return {
        "global": {
            "version": github_meta["tag_name"] + ".0",
            "urls": [github_meta["assets"][0]["browser_download_url"]]
        },
        "cn": {
            "version": cn_version,
            "urls": [cn_url]
        }
    }


snap_hutao_latest_version = update_snap_hutao_latest_version()


@router.get("/cn/patch/hutao", tags=["region:cn"])
async def generic_get_snap_hutao_latest_version_china_endpoint():
    return {
        "retcode": 0,
        "message": "CN endpoint reached",
        "data": snap_hutao_latest_version["cn"]
    }


@router.get("/cn/patch/hutao/download", tags=["region:cn"])
async def get_snap_hutao_latest_download_direct_china_endpoint():
    return RedirectResponse(snap_hutao_latest_version["cn"][0], status_code=302)


@router.get("/global/patch/hutao", tags=["region:global"])
async def generic_get_snap_hutao_latest_version_global_endpoint():
    return {
        "retcode": 0,
        "message": "Global endpoint reached",
        "data": snap_hutao_latest_version["global"]
    }


@router.get("/global/patch/hutao/download", tags=["region:global"])
async def get_snap_hutao_latest_download_direct_china_endpoint():
    return RedirectResponse(snap_hutao_latest_version["global"][0], status_code=302)


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
