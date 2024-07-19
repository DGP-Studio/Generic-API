import httpx
import os
import redis
import json
from fastapi import APIRouter, Response, status, Request, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime
from utils.dgp_utils import update_recent_versions
from utils.PatchMeta import PatchMeta, MirrorMeta
from utils.authentication import verify_api_token
from utils.redis_utils import redis_conn
from utils.stats import record_device_id
from mysql_app.schemas import StandardResponse
from config import github_headers, VALID_PROJECT_KEYS
from base_logger import logger

if redis_conn:
    try:
        logger.info(f"Got overwritten_china_url from Redis: {json.loads(redis_conn.get("snap-hutao:mirrors"))}")
    except (redis.exceptions.ConnectionError, TypeError, AttributeError):
        logger.warning("Initialing overwritten_china_url in Redis")
        for key in VALID_PROJECT_KEYS:
            r = redis_conn.set(f"{key}:mirrors", json.dumps({"version": None, "mirrors": []}))
            logger.info(f"Set [{key}:mirrors] to Redis: {r}")

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

    github_mirror = MirrorMeta(
        url=github_msix_url,
        mirror_name="GitHub"
    )

    github_path_meta = PatchMeta(
        version=github_meta["tag_name"] + ".0",
        validation=sha256sums_value if sha256sums_value else None,
        cache_time=datetime.now(),
        mirrors=[github_mirror]
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
    jihulab_patch_meta = github_patch_meta.model_copy()

    # handle Jihulab release
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

            jihulab_mirror_meta = MirrorMeta(
                url=jihulab_url,
                mirror_name="JiHuLAB"
            )

            jihulab_archive_mirror_meta = MirrorMeta(
                url=archive_url,
                mirror_name="JiHuLAB Archive"
            )
            jihulab_patch_meta.mirrors.append(jihulab_mirror_meta)
            jihulab_patch_meta.mirrors.append(jihulab_archive_mirror_meta)
            logger.debug(f"JiHuLAB data fetched: {jihulab_patch_meta}")
        except (KeyError, IndexError) as e:
            gitlab_message = f"Error occurred when fetching Snap Hutao from JiHuLAB: {e}. "
            logger.error(gitlab_message)
    logger.debug(f"GitHub data: {github_patch_meta}")

    # Clear overwritten URL if the version is updated
    try:
        hutao_mirror_list = redis_conn.get("snap-hutao:mirrors").json()
        if hutao_mirror_list["version"] != github_patch_meta.version:
            # Re-initial the mirror list with empty data
            logger.info("Found unmatched version, clearing overwritten URL")
            new_mirror_meta = {
                "version": github_patch_meta.version,
                "mirrors": []
            }
            if redis_conn:
                logger.info(f"Set snap-hutao:mirrors to Redis: {redis_conn.set("snap-hutao:mirrors",
                                                                               json.dumps(new_mirror_meta))}")
        else:
            jihulab_patch_meta.mirrors.append(hutao_mirror_list.get("mirrors"))
    except AttributeError:
        pass

    return_data = {
        "global": github_patch_meta.model_dump(),
        "cn": jihulab_patch_meta.model_dump(),
        "github_message": github_message,
        "gitlab_message": gitlab_message
    }
    if redis_conn:
        logger.info(
            f"Set Snap Hutao latest version to Redis: {redis_conn.set('snap-hutao:patch',
                                                                      json.dumps(return_data, default=str))}")
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
    return RedirectResponse(snap_hutao_latest_version["cn"]["mirrors"][0]["url"], status_code=302, headers=headers)


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
    return RedirectResponse(snap_hutao_latest_version["global"]["mirrors"][0]["url"], status_code=302)


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

@china_router.post("/mirror", tags=["admin"], include_in_schema=True,
                   dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@global_router.post("/mirror", tags=["admin"], include_in_schema=True,
                    dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
async def add_mirror_url(response: Response, request: Request) -> StandardResponse:
    """
    Update overwritten China URL for a project, this url will be placed at first priority when fetching latest version.
    **This endpoint requires API token verification**

    :param response: Response model from FastAPI

    :param request: Request model from FastAPI

    :return: Json response with message
    """
    data = await request.json()
    PROJECT_KEY = data.get("key", "").lower()
    MIRROR_URL = data.get("url", None)
    MIRROR_NAME = data.get("name", None)
    project_mirror_redis_key = f"{PROJECT_KEY}:mirrors"

    if not MIRROR_URL or not MIRROR_NAME or PROJECT_KEY not in VALID_PROJECT_KEYS:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return StandardResponse(message="Invalid request")

    current_version = json.loads(redis_conn.get(project_mirror_redis_key)).get("version")

    mirror_list = json.loads(redis_conn.get(project_mirror_redis_key)).get("mirrors")
    print(mirror_list)
    mirror_list.append(MirrorMeta(name=MIRROR_NAME, url=MIRROR_URL, version=current_version))

    # Overwrite overwritten_china_url to Redis
    if redis_conn:
        update_result = redis_conn.set(project_mirror_redis_key, json.dumps(mirror_list))
        logger.info(f"Set overwritten_china_url to Redis: {update_result}")

    # Refresh project patch
    if PROJECT_KEY == "snap-hutao":
        update_snap_hutao_latest_version()
    elif PROJECT_KEY == "snap-hutao-deployment":
        update_snap_hutao_deployment_version()
    response.status_code = status.HTTP_201_CREATED
    logger.info(f"Latest overwritten URL data: {mirror_list}")
    return StandardResponse(message=f"Successfully added {MIRROR_NAME} mirror URL for {PROJECT_KEY}",
                            data=mirror_list)


# Initial patch metadata
update_snap_hutao_latest_version()
update_snap_hutao_deployment_version()
