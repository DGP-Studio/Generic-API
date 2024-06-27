import httpx
import os
import redis
import json
import re
from fastapi import APIRouter, Response, status, Request, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime
from utils.dgp_utils import update_recent_versions
from utils.PatchMeta import PatchMeta
from utils.authentication import verify_api_token
from utils.redis_utils import redis_conn
from utils.stats import record_device_id
from mysql_app.schemas import StandardResponse
from config import github_headers, VALID_PROJECT_KEYS
from base_logger import logger

if redis_conn:
    try:
        logger.info(f"Got overwritten_china_url from Redis: {json.loads(redis_conn.get("overwritten_china_url"))}")
    except (redis.exceptions.ConnectionError, TypeError, AttributeError):
        logger.warning("Initialing overwritten_china_url in Redis")
        new_overwritten_china_url = {}
        for key in VALID_PROJECT_KEYS:
            new_overwritten_china_url[key] = {
                "version": None,
                "url": None
            }
        r = redis_conn.set("overwritten_china_url", json.dumps(new_overwritten_china_url))
        logger.info(f"Set overwritten_china_url to Redis: {r}")

"""
sample_overwritten_china_url = {
    "snap-hutao": {
        "version": "1.2.3",
        "url": "https://example.com/snap-hutao"
    },
    "snap-hutao-deployment": {
        "version": "1.2.3",
        "url": "https://example.com/snap-hutao-deployment"
    }
}
"""

china_router = APIRouter(tags=["Patch"], prefix="/patch")
global_router = APIRouter(tags=["Patch"], prefix="/patch")


def fetch_snap_hutao_github_latest_version() -> PatchMeta:
    """
    Fetch Snap Hutao latest version metadata from GitHub
    :return: PatchMeta of latest version metadata
    """

    # Output variables
    github_msix_url = None
    sha256sums_url = None
    sha256sums_value = None

    github_meta = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao/releases/latest",
                            headers=github_headers).json()

    # Patch Note
    full_description = github_meta["body"]
    try:
        ending_desc = re.search(r"## 完整更新日志(.|\r|\n)+$", full_description).group(0)
        full_description = full_description.replace(ending_desc, "")
    except AttributeError:
        pass
    split_description = full_description.split("## Update Log")
    cn_description = split_description[0].replace("## 更新日志", "") if len(split_description) > 1 else "获取日志失败"
    en_description = split_description[1] if len(split_description) > 1 else "Failed to get log"

    # Release asset (MSIX)
    for asset in github_meta["assets"]:
        if asset["name"].endswith(".msix"):
            github_msix_url = asset["browser_download_url"]
        elif asset["name"].endswith("SHA256SUMS"):
            sha256sums_url = asset["browser_download_url"]
    if github_msix_url is None:
        raise ValueError("Failed to get Snap Hutao latest version from GitHub")

    # Handle checksum file
    if sha256sums_url:
        with (open("cache/sha256sums", "wb") as f,
              httpx.stream('GET', sha256sums_url, headers=github_headers, follow_redirects=True) as response):
            response.raise_for_status()
            for chunk in response.iter_bytes():
                f.write(chunk)
        with open("cache/sha256sums", 'r') as f:
            sha256sums_value = f.read().replace("\n", "")

        os.remove("cache/sha256sums")

    """
    # 没人写应用内显示更新日志的代码
    github_path_meta = PatchMeta(
        version=github_meta["tag_name"] + ".0",
        url=[github_msix_url],
        validation=sha256sums_value if sha256sums_value else None,
        patch_note={"cn": cn_description, "en": en_description, "full": full_description},
        url_type="GitHub",
        cache_time=datetime.now()
    )
    """
    github_path_meta = PatchMeta(
        version=github_meta["tag_name"] + ".0",
        url=[github_msix_url],
        validation=sha256sums_value if sha256sums_value else None,
        patch_note={"cn": "", "en": "", "full": ""},
        url_type="GitHub",
        cache_time=datetime.now()
    )
    logger.debug(f"GitHub data fetched: {github_path_meta}")
    return github_path_meta


def update_snap_hutao_latest_version() -> dict:
    """
    Update Snap Hutao latest version from GitHub and Jihulab
    :return: dict of latest version metadata
    """
    gitlab_message = ""
    github_message = ""

    # handle GitHub release
    github_patch_meta = fetch_snap_hutao_github_latest_version()

    # handle Jihulab release
    jihulab_patch_meta = github_patch_meta.copy()
    jihulab_patch_meta.url_type = "JiHuLAB"
    jihulab_meta = httpx.get(
        "https://jihulab.com/api/v4/projects/DGP-Studio%2FSnap.Hutao/releases/permalink/latest",
        follow_redirects=True).json()
    jihu_tag_name = jihulab_meta["tag_name"] + ".0"
    if jihu_tag_name != github_patch_meta.version:
        # JiHuLAB sync not done yet
        gitlab_message = f"GitLab release not found, using GitHub release instead. "
        logger.warning(gitlab_message)
    else:
        try:
            jihulab_url = [a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                           if a["link_type"] == "package"][0]
            archive_url = [a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                           if a["name"] == "artifact_archive"][0]
            jihulab_patch_meta.url = [jihulab_url]
            jihulab_patch_meta.archive_url = [archive_url]
        except (KeyError, IndexError) as e:
            gitlab_message = f"Error occurred when fetching Snap Hutao from JiHuLAB: {e}. "
            logger.error(gitlab_message)
    logger.debug(f"JiHuLAB data fetched: {jihulab_patch_meta}")

    # Clear overwritten URL if the version is updated
    overwritten_china_url = json.loads(redis_conn.get("overwritten_china_url"))
    if overwritten_china_url["snap-hutao"]["version"] != github_patch_meta.version:
        logger.info("Found unmatched version, clearing overwritten URL")
        overwritten_china_url["snap-hutao"]["version"] = None
        overwritten_china_url["snap-hutao"]["url"] = None
        if redis_conn:
            logger.info(f"Set overwritten_china_url to Redis: {redis_conn.set("overwritten_china_url",
                                                                              json.dumps(overwritten_china_url))}")
    else:
        gitlab_message += f"Using overwritten URL: {overwritten_china_url['snap-hutao']['url']}. "
        jihulab_patch_meta.url = [overwritten_china_url["snap-hutao"]["url"]] + jihulab_patch_meta.url

    return_data = {
        "global": {
            "version": github_patch_meta.version,
            "urls": github_patch_meta.url,
            "sha256": github_patch_meta.validation,
            "archive_urls": [],
            "release_description": {
                "cn": github_patch_meta.patch_note["cn"],
                "en": github_patch_meta.patch_note["en"],
                "full": github_patch_meta.patch_note["full"]
            }
        },
        "cn": {
            "version": jihulab_patch_meta.version,
            "urls": jihulab_patch_meta.url,
            "sha256": jihulab_patch_meta.validation,
            "archive_urls": jihulab_patch_meta.archive_url,
            "release_description": {
                "cn": jihulab_patch_meta.patch_note["cn"],
                "en": jihulab_patch_meta.patch_note["en"],
                "full": jihulab_patch_meta.patch_note["full"]
            }
        },
        "github_message": github_message,
        "gitlab_message": gitlab_message
    }
    if redis_conn:
        logger.info(
            f"Set Snap Hutao latest version to Redis: {redis_conn.set('snap_hutao_latest_version', json.dumps(return_data))}")
    return return_data


def update_snap_hutao_deployment_version() -> dict:
    """
    Update Snap Hutao Deployment latest version from GitHub and Jihulab
    :return: dict of Snap Hutao Deployment latest version metadata
    """
    github_meta = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao.Deployment/releases/latest",
                            headers=github_headers).json()
    github_msix_url = None
    for asset in github_meta["assets"]:
        if asset["name"].endswith(".exe"):
            github_msix_url = [asset["browser_download_url"]]
    jihulab_meta = httpx.get(
        "https://jihulab.com/api/v4/projects/DGP-Studio%2FSnap.Hutao.Deployment/releases/permalink/latest",
        follow_redirects=True).json()
    cn_urls = list([list([a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                          if a["link_type"] == "package"])[0]])

    # Clear overwritten URL if the version is updated
    overwritten_china_url = json.loads(redis_conn.get("overwritten_china_url"))
    if overwritten_china_url["snap-hutao-deployment"]["version"] != jihulab_meta["tag_name"]:
        logger.info("Found unmatched version, clearing overwritten URL")
        overwritten_china_url["snap-hutao-deployment"]["version"] = None
        overwritten_china_url["snap-hutao-deployment"]["url"] = None
        if redis_conn:
            logger.info(f"Set overwritten_china_url to Redis: {redis_conn.set("overwritten_china_url",
                                                                              json.dumps(overwritten_china_url))}")
    else:
        cn_urls = [overwritten_china_url["snap-hutao-deployment"]["url"]] + cn_urls

    return_data = {
        "global": {
            "version": github_meta["tag_name"] + ".0",
            "urls": github_msix_url
        },
        "cn": {
            "version": jihulab_meta["tag_name"] + ".0",
            "urls": cn_urls
        }
    }
    if redis_conn:
        logger.info(
            f"Set Snap Hutao Deployment latest version to Redis: {redis_conn.set('snap_hutao_deployment_latest_version', json.dumps(return_data))}")
    return return_data


# Snap Hutao
@china_router.get("/hutao", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
async def generic_get_snap_hutao_latest_version_china_endpoint() -> StandardResponse:
    """
    Get Snap Hutao latest version from China endpoint

    :return: Standard response with latest version metadata in China endpoint
    """
    snap_hutao_latest_version = json.loads(redis_conn.get("snap_hutao_latest_version"))
    return StandardResponse(
        retcode=0,
        message=f"CN endpoint reached. {snap_hutao_latest_version["gitlab_message"]}",
        data=snap_hutao_latest_version["cn"]
    )


@china_router.get("/hutao/download")
async def get_snap_hutao_latest_download_direct_china_endpoint() -> RedirectResponse:
    """
    Redirect to Snap Hutao latest download link in China endpoint (use first link in the list)

    :return: 302 Redirect to the first download link
    """
    snap_hutao_latest_version = json.loads(redis_conn.get("snap_hutao_latest_version"))
    checksum_value = snap_hutao_latest_version["cn"]["sha256"]
    headers = {
        "X-Checksum-Sha256": checksum_value
    } if checksum_value else {}
    return RedirectResponse(snap_hutao_latest_version["cn"]["urls"][0], status_code=302, headers=headers)


@global_router.get("/hutao", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
async def generic_get_snap_hutao_latest_version_global_endpoint() -> StandardResponse:
    """
    Get Snap Hutao latest version from Global endpoint (GitHub)

    :return: Standard response with latest version metadata in Global endpoint
    """
    snap_hutao_latest_version = json.loads(redis_conn.get("snap_hutao_latest_version"))
    return StandardResponse(
        retcode=0,
        message=f"Global endpoint reached. {snap_hutao_latest_version['github_message']}",
        data=snap_hutao_latest_version["global"]
    )


@global_router.get("/hutao/download")
async def get_snap_hutao_latest_download_direct_china_endpoint() -> RedirectResponse:
    """
    Redirect to Snap Hutao latest download link in Global endpoint (use first link in the list)

    :return: 302 Redirect to the first download link
    """
    snap_hutao_latest_version = json.loads(redis_conn.get("snap_hutao_latest_version"))
    return RedirectResponse(snap_hutao_latest_version["global"]["urls"][0], status_code=302)


# Snap Hutao Deployment
@china_router.get("/hutao-deployment", response_model=StandardResponse)
async def generic_get_snap_hutao_latest_version_china_endpoint() -> StandardResponse:
    """
    Get Snap Hutao Deployment latest version from China endpoint

    :return: Standard response with latest version metadata in China endpoint
    """
    snap_hutao_deployment_latest_version = json.loads(redis_conn.get("snap_hutao_deployment_latest_version"))
    return StandardResponse(
        retcode=0,
        message="CN endpoint reached",
        data=snap_hutao_deployment_latest_version["cn"]
    )


@china_router.get("/hutao-deployment/download")
async def get_snap_hutao_latest_download_direct_china_endpoint() -> RedirectResponse:
    """
    Redirect to Snap Hutao Deployment latest download link in China endpoint (use first link in the list)

    :return: 302 Redirect to the first download link
    """
    snap_hutao_deployment_latest_version = json.loads(redis_conn.get("snap_hutao_deployment_latest_version"))
    return RedirectResponse(snap_hutao_deployment_latest_version["cn"]["urls"][0], status_code=302)


@global_router.get("/hutao-deployment", response_model=StandardResponse)
async def generic_get_snap_hutao_latest_version_global_endpoint() -> StandardResponse:
    """
    Get Snap Hutao Deployment latest version from Global endpoint (GitHub)

    :return: Standard response with latest version metadata in Global endpoint
    """
    snap_hutao_deployment_latest_version = json.loads(redis_conn.get("snap_hutao_deployment_latest_version"))
    return StandardResponse(message="Global endpoint reached",
                            data=snap_hutao_deployment_latest_version["global"])


@global_router.get("/hutao-deployment/download")
async def get_snap_hutao_latest_download_direct_china_endpoint() -> RedirectResponse:
    """
    Redirect to Snap Hutao Deployment latest download link in Global endpoint (use first link in the list)

    :return: 302 Redirect to the first download link
    """
    snap_hutao_deployment_latest_version = json.loads(redis_conn.get("snap_hutao_deployment_latest_version"))
    return RedirectResponse(snap_hutao_deployment_latest_version["global"]["urls"][0], status_code=302)


@china_router.patch("/{project_key}", include_in_schema=True, response_model=StandardResponse)
@global_router.patch("/{project_key}", include_in_schema=True, response_model=StandardResponse)
async def generic_patch_latest_version(response: Response, project_key: str) -> StandardResponse:
    """
    Update latest version of a project

    :param response: Response model from FastAPI

    :param project_key: Key name of the project to update

    :return: Latest version metadata of the project updated
    """
    new_version = None
    if project_key == "snap-hutao":
        new_version = update_snap_hutao_latest_version()
        update_recent_versions()
    elif project_key == "snap-hutao-deployment":
        new_version = update_snap_hutao_deployment_version()
    response.status_code = status.HTTP_201_CREATED
    return StandardResponse(data={"version": new_version})


# Yae Patch API handled by https://github.com/Masterain98/SnapHutao-Yae-Patch-Backend
# @china_router.get("/yae") -> use Nginx reverse proxy instead
# @global_router.get("/yae") -> use Nginx reverse proxy instead

@china_router.post("/cn-overwrite-url", tags=["admin"], include_in_schema=True,
                   dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@global_router.post("/cn-overwrite-url", tags=["admin"], include_in_schema=True,
                    dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
async def update_overwritten_china_url(response: Response, request: Request) -> StandardResponse:
    """
    Update overwritten China URL for a project, this url will be placed at first priority when fetching latest version.
    **This endpoint requires API token verification**

    :param response: Response model from FastAPI

    :param request: Request model from FastAPI

    :return: Json response with message
    """
    data = await request.json()
    project_key = data.get("key", "").lower()
    overwrite_url = data.get("url", None)
    overwritten_china_url = json.loads(redis_conn.get("overwritten_china_url"))
    if data["key"] in VALID_PROJECT_KEYS:
        if project_key == "snap-hutao":
            snap_hutao_latest_version = json.loads(redis_conn.get("snap_hutao_latest_version"))
            current_version = snap_hutao_latest_version["cn"]["version"]
        elif project_key == "snap-hutao-deployment":
            snap_hutao_deployment_latest_version = json.loads(redis_conn.get("snap_hutao_deployment_latest_version"))
            current_version = snap_hutao_deployment_latest_version["cn"]["version"]
        else:
            current_version = None
        overwritten_china_url[project_key] = {
            "version": current_version,
            "url": overwrite_url
        }

        # Overwrite overwritten_china_url to Redis
        if redis_conn:
            update_result = redis_conn.set("overwritten_china_url", json.dumps(overwritten_china_url))
            logger.info(f"Set overwritten_china_url to Redis: {update_result}")

        # Refresh project patch
        if project_key == "snap-hutao":
            update_snap_hutao_latest_version()
        elif project_key == "snap-hutao-deployment":
            update_snap_hutao_deployment_version()
        response.status_code = status.HTTP_201_CREATED
        logger.info(f"Latest overwritten URL data: {overwritten_china_url}")
        return StandardResponse(message=f"Successfully overwritten {project_key} url to {overwrite_url}",
                                data=overwritten_china_url)


# Initial patch metadata
update_snap_hutao_latest_version()
update_snap_hutao_deployment_version()
