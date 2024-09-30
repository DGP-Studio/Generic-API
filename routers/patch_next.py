import httpx
import os
from redis import asyncio as redis
import json
from fastapi import APIRouter, Response, status, Request, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime
from pydantic.json import pydantic_encoder
from utils.dgp_utils import update_recent_versions
from utils.PatchMeta import PatchMeta, MirrorMeta
from utils.authentication import verify_api_token
from utils.stats import record_device_id
from mysql_app.schemas import StandardResponse
from config import github_headers, VALID_PROJECT_KEYS
from base_logger import logger

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
        mirror_name="GitHub",
        mirror_type="direct"
    )

    github_path_meta = PatchMeta(
        version=github_meta["tag_name"] + ".0",
        validation=sha256sums_value if sha256sums_value else None,
        cache_time=datetime.now(),
        mirrors=[github_mirror]
    )
    logger.debug(f"GitHub data fetched: {github_path_meta}")
    return github_path_meta


async def update_snap_hutao_latest_version(redis_client) -> dict:
    """
    Update Snap Hutao latest version from GitHub and Jihulab
    :return: dict of latest version metadata
    """
    gitlab_message = ""
    github_message = ""

    # handle GitHub release
    github_patch_meta = fetch_snap_hutao_github_latest_version()
    jihulab_patch_meta = github_patch_meta.model_copy(deep=True)

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
                mirror_name="JiHuLAB",
                mirror_type="direct"
            )

            jihulab_archive_mirror_meta = MirrorMeta(
                url=archive_url,
                mirror_name="JiHuLAB Archive",
                mirror_type="archive"
            )
            jihulab_patch_meta.mirrors.append(jihulab_mirror_meta)
            jihulab_patch_meta.mirrors.append(jihulab_archive_mirror_meta)
            logger.debug(f"JiHuLAB data fetched: {jihulab_patch_meta}")
        except (KeyError, IndexError) as e:
            gitlab_message = f"Error occurred when fetching Snap Hutao from JiHuLAB: {e}. "
            logger.error(gitlab_message)
    logger.debug(f"GitHub data: {github_patch_meta}")

    # Clear mirror URL if the version is updated
    try:
        redis_cached_version = redis_client.get("snap-hutao:version")
        if redis_cached_version != github_patch_meta.version:
            # Re-initial the mirror list with empty data
            logger.info(
                f"Found unmatched version, clearing mirrors URL. Deleting version [{redis_cached_version}]: {await redis_client.delete(f'snap-hutao:mirrors:{redis_cached_version}')}")
            logger.info(
                f"Set Snap Hutao latest version to Redis: {await redis_client.set('snap-hutao:version', github_patch_meta.version)}")
            logger.info(
                f"Set snap-hutao:mirrors:{jihulab_patch_meta.version} to Redis: {await redis_client.set(f'snap-hutao:mirrors:{jihulab_patch_meta.version}', json.dumps([]))}")
        else:
            current_mirrors = json.loads(await redis_client.get(f"snap-hutao:mirrors:{jihulab_patch_meta.version}"))
            for m in current_mirrors:
                this_mirror = MirrorMeta(**m)
                jihulab_patch_meta.mirrors.append(this_mirror)
    except AttributeError:
        pass

    return_data = {
        "global": github_patch_meta.model_dump(),
        "cn": jihulab_patch_meta.model_dump(),
        "github_message": github_message,
        "gitlab_message": gitlab_message
    }
    logger.info(f"Set Snap Hutao latest version to Redis: {await redis_client.set('snap-hutao:patch',
                                                                                  json.dumps(return_data, default=str))}")
    return return_data


async def update_snap_hutao_deployment_version(redis_client) -> dict:
    """
    Update Snap Hutao Deployment latest version from GitHub and Jihulab
    :return: dict of Snap Hutao Deployment latest version metadata
    """
    github_meta = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao.Deployment/releases/latest",
                            headers=github_headers).json()
    github_exe_url = None
    for asset in github_meta["assets"]:
        if asset["name"].endswith(".exe"):
            github_exe_url = asset["browser_download_url"]
    if github_exe_url is None:
        raise ValueError("Failed to get Snap Hutao Deployment latest version from GitHub")
    github_patch_meta = PatchMeta(
        version=github_meta["tag_name"] + ".0",
        validation="",
        cache_time=datetime.now(),
        mirrors=[MirrorMeta(url=github_exe_url, mirror_name="GitHub", mirror_type="direct")]
    )
    jihulab_meta = httpx.get(
        "https://jihulab.com/api/v4/projects/DGP-Studio%2FSnap.Hutao.Deployment/releases/permalink/latest",
        follow_redirects=True).json()
    cn_urls = list([list([a["direct_asset_url"] for a in jihulab_meta["assets"]["links"]
                          if a["link_type"] == "package"])[0]])
    if len(cn_urls) == 0:
        raise ValueError("Failed to get Snap Hutao Deployment latest version from JiHuLAB")
    jihulab_patch_meta = PatchMeta(
        version=jihulab_meta["tag_name"] + ".0",
        validation="",
        cache_time=datetime.now(),
        mirrors=[MirrorMeta(url=cn_urls[0], mirror_name="JiHuLAB", mirror_type="direct")]
    )

    current_cached_version = redis_client.get("snap-hutao-deployment:version")
    if current_cached_version != jihulab_meta["tag_name"]:
        logger.info(
            f"Found unmatched version, clearing mirrors. Setting Snap Hutao Deployment latest version to Redis: {await redis_client.set('snap-hutao-deployment:version', jihulab_patch_meta.version)}")
        logger.info(
            f"Reinitializing mirrors for Snap Hutao Deployment: {await redis_client.set(f'snap-hutao-deployment:mirrors:{await jihulab_patch_meta.version}', json.dumps([]))}")
    else:
        current_mirrors = json.loads(redis_client.get(f"snap-hutao-deployment:mirrors:{jihulab_patch_meta.version}"))
        for m in current_mirrors:
            this_mirror = MirrorMeta(**m)
            jihulab_patch_meta.mirrors.append(this_mirror)

    return_data = {
        "global": github_patch_meta.model_dump(),
        "cn": jihulab_patch_meta.model_dump()
    }
    logger.info(f"Set Snap Hutao Deployment latest version to Redis: "
                f"{await redis_client.set('snap-hutao-deployment:patch', json.dumps(return_data, default=pydantic_encoder))}")
    return return_data


# Snap Hutao
@china_router.get("/hutao", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
async def generic_get_snap_hutao_latest_version_china_endpoint(redis_client) -> StandardResponse:
    """
    Get Snap Hutao latest version from China endpoint

    :return: Standard response with latest version metadata in China endpoint
    """
    snap_hutao_latest_version = json.loads(redis_client.get("snap-hutao:patch"))

    # For compatibility purposes
    return_data = snap_hutao_latest_version["cn"]
    urls = [m["url"] for m in snap_hutao_latest_version["cn"]["mirrors"] if "archive" not in m["url"]]
    urls.reverse()
    return_data["urls"] = urls
    return_data["sha256"] = snap_hutao_latest_version["cn"]["validation"]

    return StandardResponse(
        retcode=0,
        message=f"CN endpoint reached. {snap_hutao_latest_version["gitlab_message"]}",
        data=return_data
    )


@china_router.get("/hutao/download")
async def get_snap_hutao_latest_download_direct_china_endpoint(request: Request) -> RedirectResponse:
    """
    Redirect to Snap Hutao latest download link in China endpoint (use first link in the list)

    :return: 302 Redirect to the first download link
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    snap_hutao_latest_version = json.loads(redis_client.get("snap-hutao:patch"))
    checksum_value = snap_hutao_latest_version["cn"]["validation"]
    headers = {
        "X-Checksum-Sha256": checksum_value
    } if checksum_value else {}
    return RedirectResponse(snap_hutao_latest_version["cn"]["mirrors"][-1]["url"], status_code=302, headers=headers)


@global_router.get("/hutao", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
async def generic_get_snap_hutao_latest_version_global_endpoint(request: Request) -> StandardResponse:
    """
    Get Snap Hutao latest version from Global endpoint (GitHub)

    :return: Standard response with latest version metadata in Global endpoint
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    snap_hutao_latest_version = json.loads(redis_client.get("snap-hutao:patch"))

    # For compatibility purposes
    return_data = snap_hutao_latest_version["global"]
    urls = [m["url"] for m in snap_hutao_latest_version["global"]["mirrors"] if "archive" not in m["url"]]
    urls.reverse()
    return_data["urls"] = urls
    return_data["sha256"] = snap_hutao_latest_version["cn"]["validation"]

    return StandardResponse(
        retcode=0,
        message=f"Global endpoint reached. {snap_hutao_latest_version['github_message']}",
        data=return_data
    )


@global_router.get("/hutao/download")
async def get_snap_hutao_latest_download_direct_china_endpoint(request: Request) -> RedirectResponse:
    """
    Redirect to Snap Hutao latest download link in Global endpoint (use first link in the list)

    :return: 302 Redirect to the first download link
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    snap_hutao_latest_version = json.loads(redis_client.get("snap-hutao:patch"))
    checksum_value = snap_hutao_latest_version["global"]["validation"]
    headers = {
        "X-Checksum-Sha256": checksum_value
    } if checksum_value else {}
    return RedirectResponse(snap_hutao_latest_version["global"]["mirrors"][-1]["url"], status_code=302, headers=headers)


# Snap Hutao Deployment
@china_router.get("/hutao-deployment", response_model=StandardResponse)
async def generic_get_snap_hutao_latest_version_china_endpoint(request: Request) -> StandardResponse:
    """
    Get Snap Hutao Deployment latest version from China endpoint

    :return: Standard response with latest version metadata in China endpoint
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    snap_hutao_deployment_latest_version = json.loads(redis_client.get("snap-hutao-deployment:patch"))

    # For compatibility purposes
    return_data = snap_hutao_deployment_latest_version["cn"]
    urls = [m["url"] for m in snap_hutao_deployment_latest_version["cn"]["mirrors"] if "archive" not in m["url"]]
    urls.reverse()
    return_data["urls"] = urls
    return_data["sha256"] = snap_hutao_deployment_latest_version["cn"]["validation"]

    return StandardResponse(
        retcode=0,
        message="CN endpoint reached",
        data=return_data
    )


@china_router.get("/hutao-deployment/download")
async def get_snap_hutao_latest_download_direct_china_endpoint(request: Request) -> RedirectResponse:
    """
    Redirect to Snap Hutao Deployment latest download link in China endpoint (use first link in the list)

    :return: 302 Redirect to the first download link
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    snap_hutao_deployment_latest_version = json.loads(redis_client.get("snap-hutao-deployment:patch"))
    return RedirectResponse(snap_hutao_deployment_latest_version["cn"]["mirrors"][-1]["url"], status_code=302)


@global_router.get("/hutao-deployment", response_model=StandardResponse)
async def generic_get_snap_hutao_latest_version_global_endpoint(request: Request) -> StandardResponse:
    """
    Get Snap Hutao Deployment latest version from Global endpoint (GitHub)

    :return: Standard response with latest version metadata in Global endpoint
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    snap_hutao_deployment_latest_version = json.loads(redis_client.get("snap-hutao-deployment:patch"))

    # For compatibility purposes
    return_data = snap_hutao_deployment_latest_version["global"]
    urls = [m["url"] for m in snap_hutao_deployment_latest_version["global"]["mirrors"] if "archive" not in m["url"]]
    urls.reverse()
    return_data["urls"] = urls
    return_data["sha256"] = snap_hutao_deployment_latest_version["cn"]["validation"]

    return StandardResponse(message="Global endpoint reached",
                            data=return_data)


@global_router.get("/hutao-deployment/download")
async def get_snap_hutao_latest_download_direct_china_endpoint(request: Request) -> RedirectResponse:
    """
    Redirect to Snap Hutao Deployment latest download link in Global endpoint (use first link in the list)

    :return: 302 Redirect to the first download link
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    snap_hutao_deployment_latest_version = json.loads(redis_client.get("snap-hutao-deployment:patch"))
    return RedirectResponse(snap_hutao_deployment_latest_version["global"]["mirrors"][-1]["url"], status_code=302)


@china_router.patch("/{project_key}", include_in_schema=True, response_model=StandardResponse)
@global_router.patch("/{project_key}", include_in_schema=True, response_model=StandardResponse)
async def generic_patch_latest_version(request: Request, response: Response, project_key: str) -> StandardResponse:
    """
    Update latest version of a project

    :param request: Request model from FastAPI

    :param response: Response model from FastAPI

    :param project_key: Key name of the project to update

    :return: Latest version metadata of the project updated
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    new_version = None
    if project_key == "snap-hutao":
        new_version = update_snap_hutao_latest_version(redis_client)
        update_recent_versions(redis_client)
    elif project_key == "snap-hutao-deployment":
        new_version = update_snap_hutao_deployment_version(redis_client)
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
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    data = await request.json()
    PROJECT_KEY = data.get("key", "").lower()
    MIRROR_URL = data.get("url", None)
    MIRROR_NAME = data.get("mirror_name", None)
    MIRROR_TYPE = data.get("mirror_type", None)
    current_version = redis_client.get(f"{PROJECT_KEY}:version")
    project_mirror_redis_key = f"{PROJECT_KEY}:mirrors:{current_version}"

    if not MIRROR_URL or not MIRROR_NAME or not MIRROR_TYPE or PROJECT_KEY not in VALID_PROJECT_KEYS:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return StandardResponse(message="Invalid request")

    try:
        mirror_list = json.loads(redis_client.get(project_mirror_redis_key))
    except TypeError:
        mirror_list = []
    current_mirror_names = [m["mirror_name"] for m in mirror_list]
    if MIRROR_NAME in current_mirror_names:
        method = "updated"
        # Update the url
        for m in mirror_list:
            if m["mirror_name"] == MIRROR_NAME:
                m["url"] = MIRROR_URL
    else:
        method = "added"
        mirror_list.append(MirrorMeta(mirror_name=MIRROR_NAME, url=MIRROR_URL, mirror_type=MIRROR_TYPE))
    logger.info(f"{method.capitalize()} {MIRROR_NAME} mirror URL for {PROJECT_KEY} to {MIRROR_URL}")

    # Overwrite overwritten_china_url to Redis
    update_result = redis_client.set(project_mirror_redis_key, json.dumps(mirror_list, default=pydantic_encoder))
    logger.info(f"Set {project_mirror_redis_key} to Redis: {update_result}")

    # Refresh project patch
    if PROJECT_KEY == "snap-hutao":
        update_snap_hutao_latest_version(redis_client)
    elif PROJECT_KEY == "snap-hutao-deployment":
        update_snap_hutao_deployment_version(redis_client)
    response.status_code = status.HTTP_201_CREATED
    logger.info(f"Latest overwritten URL data: {mirror_list}")
    return StandardResponse(message=f"Successfully {method} {MIRROR_NAME} mirror URL for {PROJECT_KEY}",
                            data=mirror_list)


@china_router.delete("/mirror", tags=["admin"], include_in_schema=True,
                     dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@global_router.delete("/mirror", tags=["admin"], include_in_schema=True,
                      dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
async def delete_mirror_url(response: Response, request: Request) -> StandardResponse:
    """
    Delete overwritten China URL for a project, this url will be placed at first priority when fetching latest version.
    **This endpoint requires API token verification**

    :param response: Response model from FastAPI

    :param request: Request model from FastAPI

    :return: Json response with message
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    data = await request.json()
    PROJECT_KEY = data.get("key", "").lower()
    MIRROR_NAME = data.get("mirror_name", None)
    current_version = redis_client.get(f"{PROJECT_KEY}:version")
    project_mirror_redis_key = f"{PROJECT_KEY}:mirrors:{current_version}"

    if not MIRROR_NAME or PROJECT_KEY not in VALID_PROJECT_KEYS:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return StandardResponse(message="Invalid request")

    try:
        mirror_list = json.loads(redis_client.get(project_mirror_redis_key))
    except TypeError:
        mirror_list = []
    current_mirror_names = [m["mirror_name"] for m in mirror_list]
    if MIRROR_NAME in current_mirror_names:
        method = "deleted"
        # Remove the url
        for m in mirror_list:
            if m["mirror_name"] == MIRROR_NAME:
                mirror_list.remove(m)
    else:
        method = "not found"
    logger.info(f"{method.capitalize()} {MIRROR_NAME} mirror URL for {PROJECT_KEY}")

    # Overwrite mirror link to Redis
    update_result = redis_client.set(project_mirror_redis_key, json.dumps(mirror_list, default=pydantic_encoder))
    logger.info(f"Set {project_mirror_redis_key} to Redis: {update_result}")

    # Refresh project patch
    if PROJECT_KEY == "snap-hutao":
        update_snap_hutao_latest_version(redis_client)
    elif PROJECT_KEY == "snap-hutao-deployment":
        update_snap_hutao_deployment_version(redis_client)
    response.status_code = status.HTTP_201_CREATED
    logger.info(f"Latest overwritten URL data: {mirror_list}")
    return StandardResponse(message=f"Successfully {method} {MIRROR_NAME} mirror URL for {PROJECT_KEY}",
                            data=mirror_list)
