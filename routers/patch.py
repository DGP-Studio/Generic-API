import httpx
import os
from fastapi import APIRouter, Response, status, Request, Depends
from fastapi.responses import RedirectResponse
from utils.dgp_utils import timely_update_allowed_ua
from config import github_headers, VALID_PROJECT_KEYS
from utils.authentication import verify_api_token
from base_logger import logger
import redis
import json
import re

if os.getenv("NO_REDIS", "false").lower() == "true":
    logger.info("Skipping Redis connection in Wallpaper module as NO_REDIS is set to true")
    redis_conn = None
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    logger.info(f"Connecting to Redis at {REDIS_HOST} for patch module")
    redis_conn = redis.Redis(host=REDIS_HOST, port=6379, db=1, decode_responses=True)
    logger.info("Redis connection established for patch module")

try:
    overwritten_china_url = json.loads(redis_conn.get("overwritten_china_url"))
except (redis.exceptions.ConnectionError, TypeError, AttributeError):
    logger.warning("Failed to get overwritten_china_url from Redis, using empty dict")
    overwritten_china_url = {}
    for key in VALID_PROJECT_KEYS:
        overwritten_china_url[key] = None

router = APIRouter(tags=["category:patch"])


def update_snap_hutao_latest_version() -> dict:
    github_msix_url = None
    sha256sums_url = None
    sha256sums_value = None
    gitlab_message = ""
    github_message = ""
    archive_url = None

    # handle GitHub release
    github_meta = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao/releases/latest",
                            headers=github_headers).json()

    full_description = github_meta["body"]
    try:
        ending_desc = re.search(r"## 完整更新日志(.|\r|\n)+$", full_description).group(0)
        full_description = full_description.replace(ending_desc, "")
    except AttributeError:
        pass
    split_description = full_description.split("## Update Log")
    cn_description = split_description[0].replace("## 更新日志", "") if len(split_description) > 1 else "获取日志失败"
    en_description = split_description[1] if len(split_description) > 1 else "Failed to get log"

    for asset in github_meta["assets"]:
        if asset["name"].endswith(".msix"):
            github_msix_url = [asset["browser_download_url"]]
        elif asset["name"].endswith("SHA256SUMS"):
            sha256sums_url = asset["browser_download_url"]

    if sha256sums_url:
        with open("cache/sha256sums", "wb") as f:
            with httpx.stream('GET', sha256sums_url, headers=github_headers, follow_redirects=True) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    f.write(chunk)

        with open("cache/sha256sums", 'r') as f:
            sha256sums_value = f.read().replace("\n", "")

        os.remove("cache/sha256sums")

    # handle Jihulab release
    jihulab_meta = httpx.get(
        "https://jihulab.com/api/v4/projects/DGP-Studio%2FSnap.Hutao/releases/permalink/latest",
        follow_redirects=True).json()
    try:
        cn_version = jihulab_meta["tag_name"] + ".0"
        if overwritten_china_url["snap-hutao"]:
            cn_url = [overwritten_china_url["snap-hutao"],
                      list([a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                            if a["link_type"] == "package"])[0]]
        else:
            cn_url = [list([a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                            if a["link_type"] == "package"])[0]]
        archive_url = [list([a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                             if a["name"] == "artifact_archive"])[0]]
    except (KeyError, IndexError):
        cn_version = github_meta["tag_name"] + ".0"
        cn_url = overwritten_china_url["snap-hutao"] if overwritten_china_url["snap-hutao"] else github_msix_url
        gitlab_message += "GitLab release not found, using GitHub release instead. "

    return {
        "global": {
            "version": github_meta["tag_name"] + ".0",
            "urls": github_msix_url,
            "sha256": sha256sums_value if sha256sums_value else None,
            "archive_urls": [],
            "release_description": {
                "cn": cn_description,
                "en": en_description,
                "full": full_description
            }
        },
        "cn": {
            "version": cn_version,
            "urls": cn_url,
            "sha256": sha256sums_value if sha256sums_value else None,
            "archive_urls": archive_url,
            "release_description": {
                "cn": cn_description,
                "en": en_description,
                "full": full_description
            }
        },
        "github_message": github_message,
        "gitlab_message": gitlab_message
    }


def update_snap_hutao_deployment_version():
    github_meta = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao.Deployment/releases/latest",
                            headers=github_headers).json()
    github_msix_url = None
    for asset in github_meta["assets"]:
        if asset["name"].endswith(".exe"):
            github_msix_url = [asset["browser_download_url"]]
    jihulab_meta = httpx.get(
        "https://jihulab.com/api/v4/projects/DGP-Studio%2FSnap.Hutao.Deployment/releases/permalink/latest",
        follow_redirects=True).json()
    if overwritten_china_url["snap-hutao-deployment"]:
        cn_urls = [overwritten_china_url["snap-hutao-deployment"]] + list(
            [list([a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                   if a["link_type"] == "package"])[0]])
    else:
        cn_urls = list([list([a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                              if a["link_type"] == "package"])[0]])
    return {
        "global": {
            "version": github_meta["tag_name"] + ".0",
            "urls": github_msix_url
        },
        "cn": {
            "version": jihulab_meta["tag_name"] + ".0",
            "urls": cn_urls
        }
    }


snap_hutao_latest_version = update_snap_hutao_latest_version()
snap_hutao_deployment_latest_version = update_snap_hutao_deployment_version()


# Snap Hutao
@router.get("/cn/patch/hutao", tags=["region:cn"])
async def generic_get_snap_hutao_latest_version_china_endpoint():
    return {
        "retcode": 0,
        "message": f"CN endpoint reached. {snap_hutao_latest_version["gitlab_message"]}",
        "data": snap_hutao_latest_version["cn"]
    }


@router.get("/cn/patch/hutao/download", tags=["region:cn"])
async def get_snap_hutao_latest_download_direct_china_endpoint():
    return RedirectResponse(snap_hutao_latest_version["cn"]["urls"][0], status_code=302)


@router.get("/global/patch/hutao", tags=["region:global"])
async def generic_get_snap_hutao_latest_version_global_endpoint():
    return {
        "retcode": 0,
        "message": f"Global endpoint reached. {snap_hutao_latest_version['github_message']}",
        "data": snap_hutao_latest_version["global"]
    }


@router.get("/global/patch/hutao/download", tags=["region:global"])
async def get_snap_hutao_latest_download_direct_china_endpoint():
    return RedirectResponse(snap_hutao_latest_version["global"]["urls"][0], status_code=302)


# Snap Hutao Deployment
@router.get("/cn/patch/hutao-deployment", tags=["region:cn"])
async def generic_get_snap_hutao_latest_version_china_endpoint():
    return {
        "retcode": 0,
        "message": f"CN endpoint reached.",
        "data": snap_hutao_deployment_latest_version["cn"]
    }


@router.get("/cn/patch/hutao-deployment/download", tags=["region:cn"])
async def get_snap_hutao_latest_download_direct_china_endpoint():
    return RedirectResponse(snap_hutao_deployment_latest_version["cn"]["urls"][0], status_code=302)


@router.get("/global/patch/hutao-deployment", tags=["region:global"])
async def generic_get_snap_hutao_latest_version_global_endpoint():
    return {
        "retcode": 0,
        "message": f"Global endpoint reached.",
        "data": snap_hutao_deployment_latest_version["global"]
    }


@router.get("/global/patch/hutao-deployment/download", tags=["region:global"])
async def get_snap_hutao_latest_download_direct_china_endpoint():
    return RedirectResponse(snap_hutao_deployment_latest_version["global"]["urls"][0], status_code=302)


@router.patch("/cn/patch/{project_key}", tags=["region:cn"], include_in_schema=False)
@router.patch("/global/patch/{project_key}", tags=["region:global"], include_in_schema=False)
async def generic_patch_latest_version(response: Response, project_key: str):
    new_version = None
    if project_key == "snap-hutao":
        global snap_hutao_latest_version
        snap_hutao_latest_version = update_snap_hutao_latest_version()
        timely_update_allowed_ua()
        new_version = snap_hutao_latest_version
    elif project_key == "snap-hutao-deployment":
        global snap_hutao_deployment_latest_version
        snap_hutao_deployment_latest_version = update_snap_hutao_deployment_version()
        new_version = snap_hutao_deployment_latest_version
    response.status_code = status.HTTP_201_CREATED
    return {"version": new_version}


# Yae Patch API handled by https://github.com/Masterain98/SnapHutao-Yae-Patch-Backend
# @router.get("/cn/patch/yae") -> use Nginx reverse proxy instead
# @router.get("/global/patch/yae") -> use Nginx reverse proxy instead

@router.post("/cn/patch/cn-overwrite-url", tags=["admin"], include_in_schema=True,
             dependencies=[Depends(verify_api_token)])
@router.post("/global/patch/cn-overwrite-url", tags=["admin"], include_in_schema=True,
             dependencies=[Depends(verify_api_token)])
async def update_overwritten_china_url(response: Response, request: Request):
    data = await request.json()
    project_key = data.get("key", "").lower()
    overwrite_url = data.get("url", None)
    if data["key"] in VALID_PROJECT_KEYS:
        overwritten_china_url[project_key] = overwrite_url
        if redis_conn:
            result = redis_conn.set("overwritten_china_url", json.dumps(overwritten_china_url))
            logger.info(f"Set overwritten_china_url to Redis: {result}")
        if project_key == "snap-hutao":
            global snap_hutao_latest_version
            snap_hutao_latest_version = update_snap_hutao_latest_version()
        elif project_key == "snap-hutao-deployment":
            global snap_hutao_deployment_latest_version
            snap_hutao_deployment_latest_version = update_snap_hutao_deployment_version()
        response.status_code = status.HTTP_201_CREATED
        return {"message": f"Successfully overwritten {project_key} url to {overwrite_url}"}
