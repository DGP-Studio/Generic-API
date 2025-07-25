import httpx
import os
from redis import asyncio as aioredis
import json
from fastapi import APIRouter, Response, status, Request, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime
from pydantic.json import pydantic_encoder
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from utils.dgp_utils import update_recent_versions
from utils.PatchMeta import PatchMeta, MirrorMeta
from utils.authentication import verify_api_token
from utils.stats import record_device_id
from mysql_app.schemas import StandardResponse
from config import github_headers, VALID_PROJECT_KEYS
from base_logger import get_logger
from typing import Literal

logger = get_logger(__name__)
china_router = APIRouter(tags=["Patch"], prefix="/patch")
global_router = APIRouter(tags=["Patch"], prefix="/patch")
fujian_router = APIRouter(tags=["Patch"], prefix="/patch")


def fetch_snap_hutao_github_latest_version() -> PatchMeta:
    """
    ## Fetch Snap Hutao GitHub Latest Version

    Fetches the latest release metadata from GitHub for Snap Hutao. Extracts the MSIX asset download URL and, if available, the SHA256SUMS.
    
    **Restrictions:**
    - Requires valid GitHub headers.
    - Raises ValueError if the MSIX asset is missing.
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

    github_file_name = github_msix_url.split("/")[-1]
    github_mirror = MirrorMeta(
        url=github_msix_url,
        mirror_name="GitHub",
        mirror_type="direct"
    )

    github_path_meta = PatchMeta(
        version=github_meta["tag_name"] + ".0",
        validation=sha256sums_value if sha256sums_value else None,
        cache_time=datetime.now(),
        file_name=github_file_name,
        mirrors=[github_mirror]
    )
    logger.debug(f"GitHub data fetched: {github_path_meta}")
    return github_path_meta


async def update_snap_hutao_latest_version(redis_client: aioredis.client.Redis) -> dict:
    """
    ## Update Snap Hutao Latest Version (GitHub)

    Retrieves the latest Snap Hutao version from GitHub, updates Redis cache, and merges any overridden mirror URLs.
    
    **Restrictions:**
    - Expects a valid Redis client.
    - Assumes data in Redis is correctly formatted.
    """
    github_message = ""

    # handle GitHub release
    github_patch_meta = fetch_snap_hutao_github_latest_version()
    cn_patch_meta = github_patch_meta.model_copy(deep=True)
    logger.debug(f"GitHub data: {github_patch_meta}")

    # Clear mirror URL if the version is updated
    try:
        redis_cached_version = await redis_client.get("snap-hutao:version")
        redis_cached_version = str(redis_cached_version.decode("utf-8"))
        if redis_cached_version != github_patch_meta.version:
            logger.info(f"Find update for Snap Hutao version: {redis_cached_version} -> {github_patch_meta.version}")
            # Re-initial the mirror list with empty data
            logger.info(
                f"Found unmatched version, clearing mirrors URL. Deleting version [{redis_cached_version}]: {await redis_client.delete(f'snap-hutao:mirrors:{redis_cached_version}')}")
            logger.info(
                f"Set Snap Hutao latest version to Redis: {await redis_client.set('snap-hutao:version', github_patch_meta.version)}")
        else:
            try:
                current_mirrors = await redis_client.get(f"snap-hutao:mirrors:{cn_patch_meta.version}")
                current_mirrors = json.loads(current_mirrors)
            except TypeError:
                current_mirrors = []
            for m in current_mirrors:
                this_mirror = MirrorMeta(**m)
                cn_patch_meta.mirrors.append(this_mirror)
    except AttributeError:
        pass

    return_data = {
        "global": github_patch_meta.model_dump(),
        "cn": cn_patch_meta.model_dump(),
        "github_message": github_message,
        "gitlab_message": github_message
    }
    logger.info(f"Set Snap Hutao latest version to Redis: {await redis_client.set('snap-hutao:patch',
                                                                                  json.dumps(return_data, default=str))}")
    return return_data


async def update_snap_hutao_deployment_version(redis_client: aioredis.client.Redis) -> dict:
    """
    ## Update Snap Hutao Deployment Latest Version (GitHub)

    Retrieves and updates Snap Hutao Deployment version information from GitHub. Updates mirror URLs in Redis.
    
    **Restrictions:**
    - Raises ValueError if the executable asset is not found.
    - Requires a valid Redis client.
    """
    github_meta = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao.Deployment/releases/latest",
                            headers=github_headers).json()
    exe_file_name = None
    github_exe_url = None
    for asset in github_meta["assets"]:
        if asset["name"].endswith(".exe"):
            github_exe_url = asset["browser_download_url"]
            exe_file_name = asset["name"]
    if github_exe_url is None:
        raise ValueError("Failed to get Snap Hutao Deployment latest version from GitHub")
    github_patch_meta = PatchMeta(
        version=github_meta["tag_name"] + ".0",
        validation="",
        cache_time=datetime.now(),
        file_name=exe_file_name,
        mirrors=[MirrorMeta(url=github_exe_url, mirror_name="GitHub", mirror_type="direct")]
    )
    cn_patch_meta = github_patch_meta.model_copy(deep=True)
    static_deployment_mirror_list = [
        MirrorMeta(
            url="https://api.qhy04.com/hutaocdn/deployment",
            mirror_name="QHY CDN",
            mirror_type="direct"
        )
    ]
    cn_patch_meta.mirrors = static_deployment_mirror_list

    current_cached_version = await redis_client.get("snap-hutao-deployment:version")
    current_cached_version = current_cached_version.decode("utf-8")
    logger.info(f"Current cached version: {current_cached_version}; Latest GitHub version: {cn_patch_meta.version}")
    if current_cached_version != cn_patch_meta.version:
        logger.info(
            f"Found unmatched version, clearing mirrors. Setting Snap Hutao Deployment latest version to Redis: {await redis_client.set('snap-hutao-deployment:version', cn_patch_meta.version)}")
        logger.info(
            f"Reinitializing mirrors for Snap Hutao Deployment: {await redis_client.set(f'snap-hutao-deployment:mirrors:{cn_patch_meta.version}', json.dumps(cn_patch_meta.mirrors, default=pydantic_encoder))}")
    else:
        try:
            current_mirrors = json.loads(
                await redis_client.get(f"snap-hutao-deployment:mirrors:{cn_patch_meta.version}"))
            for m in current_mirrors:
                this_mirror = MirrorMeta(**m)
                cn_patch_meta.mirrors.append(this_mirror)
        except TypeError:
            # New initialization
            mirror_json = json.dumps(cn_patch_meta.mirrors, default=pydantic_encoder)
            await redis_client.set(f"snap-hutao-deployment:mirrors:{cn_patch_meta.version}", mirror_json)

    return_data = {
        "global": github_patch_meta.model_dump(),
        "cn": cn_patch_meta.model_dump()
    }
    logger.info(f"Set Snap Hutao Deployment latest version to Redis: "
                f"{await redis_client.set('snap-hutao-deployment:patch', json.dumps(return_data, default=pydantic_encoder))}")
    return return_data


async def fetch_snap_hutao_alpha_latest_version(redis_client: aioredis.client.Redis) -> dict | None:
    """
    ## Fetch Snap Hutao Alpha Latest Version (GitHub Actions)

    Retrieves the latest Snap Hutao Alpha version using GitHub Actions workflow runs and artifacts.
    
    **Restrictions:**
    - Returns None if no successful workflow run meeting criteria is found.
    - Requires valid GitHub Actions response.
    """
    # Fetch the workflow runs
    github_meta = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao/actions/workflows/alpha.yml/runs",
                            headers=github_headers)
    runs = github_meta.json()["workflow_runs"]

    # Find the latest successful run
    latest_successful_run = next((run for run in runs if run["conclusion"] == "success"
                                  and run["head_branch"] == "develop"), None)
    if not latest_successful_run:
        logger.error("No successful Snap Hutao Alpha workflow runs found.")
        return None

    run_id = latest_successful_run["id"]
    artifacts_url = f"https://api.github.com/repos/DGP-Studio/Snap.Hutao/actions/runs/{run_id}/artifacts"

    # Fetch artifacts for the successful run
    artifacts_response = httpx.get(artifacts_url, headers=github_headers)
    artifacts = artifacts_response.json()["artifacts"]

    # Extract asset download URLs
    asset_urls = [
        {
            "name": artifact["name"].replace("Snap.Hutao.Alpha-", ""),
            "download_url": f"https://github.com/DGP-Studio/Snap.Hutao/actions/runs/{run_id}/artifacts/{artifact['id']}"
        }
        for artifact in artifacts if artifact["expired"] is False and artifact["name"].startswith("Snap.Hutao.Alpha")
    ]

    if not asset_urls:
        logger.error("No Snap Hutao Alpha artifacts found.")
        return None

    # Print the assets
    github_mirror = MirrorMeta(
        url=asset_urls[0]["download_url"],
        mirror_name="GitHub",
        mirror_type="browser"
    )

    github_path_meta = PatchMeta(
        version=asset_urls[0]["name"],
        validation="",
        cache_time=datetime.now(),
        mirrors=[github_mirror],
        file_name=asset_urls[0]["name"]
    )

    resp = await redis_client.set("snap-hutao-alpha:patch",
                                  json.dumps(github_path_meta.model_dump(), default=str),
                                  ex=60 * 10)
    logger.info(f"Set Snap Hutao Alpha latest version to Redis: {resp} {github_path_meta}")
    return github_path_meta.model_dump()


# Snap Hutao
@china_router.get("/hutao", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
@fujian_router.get("/hutao", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
async def generic_get_snap_hutao_latest_version_china_endpoint(request: Request) -> StandardResponse:
    """
    ## Get Snap Hutao Latest Version (China Endpoint)

    Returns the latest Snap Hutao version metadata from Redis for China users, including mirror URLs and SHA256 validation.
    
    **Restrictions:**
    - Expects valid JSON data from Redis.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    snap_hutao_latest_version = await redis_client.get("snap-hutao:patch")
    snap_hutao_latest_version = json.loads(snap_hutao_latest_version)

    # For compatibility purposes
    return_data = snap_hutao_latest_version["cn"]
    urls = [m["url"] for m in snap_hutao_latest_version["cn"]["mirrors"] if "archive" not in m["url"]]
    urls.reverse()
    return_data["urls"] = urls
    return_data["sha256"] = snap_hutao_latest_version["cn"]["validation"]

    try:
        allowed_user_agents = await redis_client.get("allowed_user_agents")
        allowed_user_agents = json.loads(allowed_user_agents)
        current_ua = request.headers.get("User-Agent", "")
        if allowed_user_agents:
            if current_ua in allowed_user_agents:
                retcode = 0
                message = f"CN endpoint reached. {snap_hutao_latest_version['gitlab_message']}"
            else:
                retcode = 418
                message = "过时的客户端，请更新到最新版本。"
        else:
            retcode = 0
            message = "CN endpoint reached."
    except TypeError:
        retcode = 0
        message = "CN endpoint reached."


    return StandardResponse(
        retcode=retcode,
        message=message,
        data=return_data
    )


@china_router.get("/hutao/download")
@fujian_router.get("/hutao/download")
async def get_snap_hutao_latest_download_direct_china_endpoint(request: Request) -> RedirectResponse:
    """
    ## Redirect to Snap Hutao Download (China Endpoint)

    Redirects the user to the primary download link for the Snap Hutao China version, appending SHA256 checksum if available.
    
    **Restrictions:**
    - Assumes available mirror URLs in Redis.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    snap_hutao_latest_version = await redis_client.get("snap-hutao:patch")
    snap_hutao_latest_version = json.loads(snap_hutao_latest_version)
    checksum_value = snap_hutao_latest_version["cn"]["validation"]
    headers = {
        "X-Checksum-Sha256": checksum_value
    } if checksum_value else {}
    return RedirectResponse(snap_hutao_latest_version["cn"]["mirrors"][-1]["url"], status_code=301, headers=headers)


@global_router.get("/hutao", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
async def generic_get_snap_hutao_latest_version_global_endpoint(request: Request) -> StandardResponse:
    """
    ## Get Snap Hutao Latest Version (Global Endpoint)

    Retrieves the Snap Hutao latest version metadata from Redis for global users, merging mirror URLs and validation data.
    
    **Restrictions:**
    - Expects properly structured Redis data.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    snap_hutao_latest_version = await redis_client.get("snap-hutao:patch")
    snap_hutao_latest_version = json.loads(snap_hutao_latest_version)

    # For compatibility purposes
    return_data = snap_hutao_latest_version["global"]
    urls = [m["url"] for m in snap_hutao_latest_version["global"]["mirrors"] if "archive" not in m["url"]]
    urls.reverse()
    return_data["urls"] = urls
    return_data["sha256"] = snap_hutao_latest_version["cn"]["validation"]

    try:
        allowed_user_agents = await redis_client.get("allowed_user_agents")
        allowed_user_agents = json.loads(allowed_user_agents)
        current_ua = request.headers.get("User-Agent", "")
        if allowed_user_agents:
            if current_ua in allowed_user_agents:
                retcode = 0
                message = f"Global endpoint reached. {snap_hutao_latest_version['github_message']}"
            else:
                retcode = 418
                message = "Outdated client, please update to the latest version. 过时的客户端版本，请更新到最新版本。"
        else:
            retcode = 0
            message = "Global endpoint reached."
    except TypeError:
        retcode = 0
        message = "Global endpoint reached."

    message = message if isinstance(message, str) else message[0]

    return StandardResponse(
        retcode=retcode,
        message=message,
        data=return_data
    )


@global_router.get("/hutao/download")
async def get_snap_hutao_latest_download_direct_china_endpoint(request: Request) -> RedirectResponse:
    """
    ## Redirect to Snap Hutao Download (Global Endpoint)

    Redirects the user to the primary download link for the Snap Hutao global version, with checksum in headers if available.
    
    **Restrictions:**
    - Assumes valid global mirror data exists in Redis.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    snap_hutao_latest_version = await redis_client.get("snap-hutao:patch")
    snap_hutao_latest_version = json.loads(snap_hutao_latest_version)
    checksum_value = snap_hutao_latest_version["global"]["validation"]
    headers = {
        "X-Checksum-Sha256": checksum_value
    } if checksum_value else {}
    return RedirectResponse(snap_hutao_latest_version["global"]["mirrors"][-1]["url"], status_code=301, headers=headers)


@china_router.get("/alpha", include_in_schema=True, response_model=StandardResponse)
@global_router.get("/alpha", include_in_schema=True, response_model=StandardResponse)
@fujian_router.get("/alpha", include_in_schema=True, response_model=StandardResponse)
async def generic_patch_snap_hutao_alpha_latest_version(request: Request) -> StandardResponse:
    """
    ## Update Snap Hutao Alpha Latest Version

    Fetches and returns the latest version metadata for Snap Hutao Alpha from GitHub Actions. Uses Redis as a cache.
    
    **Restrictions:**
    - Returns previously cached data if available.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    cached_data = await redis_client.get("snap-hutao-alpha:patch")
    if not cached_data:
        cached_data = await fetch_snap_hutao_alpha_latest_version(redis_client)
    else:
        cached_data = json.loads(cached_data)
    return StandardResponse(
        retcode=0,
        message="Alpha means testing",
        data=cached_data
    )


# Snap Hutao Deployment
@china_router.get("/hutao-deployment", response_model=StandardResponse)
@fujian_router.get("/hutao-deployment", response_model=StandardResponse)
async def generic_get_snap_hutao_latest_version_china_endpoint(request: Request) -> StandardResponse:
    """
    ## Get Snap Hutao Deployment Latest Version (China Endpoint)

    Retrieves the latest Snap Hutao Deployment metadata from Redis for China users and prepares mirror URLs.
    
    **Restrictions:**
    - Data must be available in Redis with proper formatting.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    snap_hutao_deployment_latest_version = await redis_client.get("snap-hutao-deployment:patch")
    snap_hutao_deployment_latest_version = json.loads(snap_hutao_deployment_latest_version)

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
@fujian_router.get("/hutao-deployment/download")
async def get_snap_hutao_latest_download_direct_china_endpoint(request: Request) -> RedirectResponse:
    """
    ## Redirect to Snap Hutao Deployment Download (China Endpoint)

    Redirects to the primary download URL of the Snap Hutao Deployment version in China as listed in Redis.
    
    **Restrictions:**
    - Assumes a valid mirror list exists.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    snap_hutao_deployment_latest_version = await redis_client.get("snap-hutao-deployment:patch")
    snap_hutao_deployment_latest_version = json.loads(snap_hutao_deployment_latest_version)
    return RedirectResponse(snap_hutao_deployment_latest_version["cn"]["mirrors"][-1]["url"], status_code=301)


@global_router.get("/hutao-deployment", response_model=StandardResponse)
async def generic_get_snap_hutao_latest_version_global_endpoint(request: Request) -> StandardResponse:
    """
    ## Get Snap Hutao Deployment Latest Version (Global Endpoint)

    Retrieves and returns the latest Snap Hutao Deployment version metadata for global users from Redis.
    
    **Restrictions:**
    - Expects both global and China data to be available for merging.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    snap_hutao_deployment_latest_version = await redis_client.get("snap-hutao-deployment:patch")
    snap_hutao_deployment_latest_version = json.loads(snap_hutao_deployment_latest_version)

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
    ## Redirect to Snap Hutao Deployment Download (Global Endpoint)

    Redirects to the primary download URL for the Snap Hutao Deployment version (global) as stored in Redis.
    
    **Restrictions:**
    - Valid mirror data must exist.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    snap_hutao_deployment_latest_version = await redis_client.get("snap-hutao-deployment:patch")
    snap_hutao_deployment_latest_version = json.loads(snap_hutao_deployment_latest_version)
    return RedirectResponse(snap_hutao_deployment_latest_version["global"]["mirrors"][-1]["url"], status_code=301)


@china_router.patch("/{project}", include_in_schema=True, response_model=StandardResponse)
@global_router.patch("/{project}", include_in_schema=True, response_model=StandardResponse)
@fujian_router.patch("/{project}", include_in_schema=True, response_model=StandardResponse)
async def generic_patch_latest_version(request: Request, response: Response, project: str) -> StandardResponse:
    """
    ## Update Project Latest Version

    Updates the latest version for a given project by calling the corresponding update function. Refreshes Redis cache accordingly.
    
    **Restrictions:**
    - Valid project key required; otherwise returns HTTP 404.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    new_version = None
    if project == "snap-hutao":
        new_version = await update_snap_hutao_latest_version(redis_client)
        await update_recent_versions(redis_client)
    elif project == "snap-hutao-deployment":
        new_version = await update_snap_hutao_deployment_version(redis_client)
    elif project == "snap-hutao-alpha":
        new_version = await fetch_snap_hutao_alpha_latest_version(redis_client)
        await update_recent_versions(redis_client)
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
    response.status_code = status.HTTP_201_CREATED
    return StandardResponse(data={"version": new_version})


class MirrorCreateModel(BaseModel):
    key: Literal["snap-hutao", "snap-hutao-deployment", "snap-hutao-alpha"]
    url: str
    mirror_name: str
    mirror_type: Literal["direct", "browser"]


@china_router.post("/mirror", tags=["Management"], include_in_schema=True,
                   dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@global_router.post("/mirror", tags=["Management"], include_in_schema=True,
                    dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@fujian_router.post("/mirror", tags=["Management"], include_in_schema=True,
                    dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
async def add_mirror_url(response: Response, request: Request, mirror: MirrorCreateModel) -> StandardResponse:
    """
    ## Add or Update Mirror URL

    Adds a new mirror URL or updates an existing one for a specified project. The function validates the request and updates Redis.
    
    **Restrictions:**
    - The project key must be one of the predefined VALID_PROJECT_KEYS.
    - All mirror data (url, mirror_name, mirror_type) must be non-empty.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    project_key = mirror.key.lower()
    mirror_url = mirror.url
    mirror_name = mirror.mirror_name
    mirror_type = mirror.mirror_type
    current_version = await redis_client.get(f"{project_key}:version")
    current_version = current_version.decode("utf-8")
    project_mirror_redis_key = f"{project_key}:mirrors:{current_version}"

    if not mirror_url or not mirror_name or not mirror_type or project_key not in VALID_PROJECT_KEYS:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return StandardResponse(message="Invalid request")

    try:
        mirror_list = json.loads(await redis_client.get(project_mirror_redis_key))
    except TypeError:
        mirror_list = []
    current_mirror_names = [m["mirror_name"] for m in mirror_list]
    if mirror_name in current_mirror_names:
        method = "updated"
        for m in mirror_list:
            if m["mirror_name"] == mirror_name:
                m["url"] = mirror_url
    else:
        method = "added"
        mirror_list.append(MirrorMeta(mirror_name=mirror_name, url=mirror_url, mirror_type=mirror_type))
    logger.info(f"{method.capitalize()} {mirror_name} mirror URL for {project_key} to {mirror_url}")

    update_result = await redis_client.set(project_mirror_redis_key, json.dumps(mirror_list, default=pydantic_encoder))
    logger.info(f"Set {project_mirror_redis_key} to Redis: {update_result}")

    if project_key == "snap-hutao":
        await update_snap_hutao_latest_version(redis_client)
    elif project_key == "snap-hutao-deployment":
        await update_snap_hutao_deployment_version(redis_client)
    response.status_code = status.HTTP_201_CREATED
    logger.info(f"Latest overwritten URL data: {mirror_list}")
    return StandardResponse(message=f"Successfully {method} {mirror_name} mirror URL for {project_key}",
                            data=mirror_list)


class MirrorDeleteModel(BaseModel):
    project_name: Literal["snap-hutao", "snap-hutao-deployment", "snap-hutao-alpha"]
    mirror_name: str


@china_router.delete("/mirror", tags=["Management"], include_in_schema=True,
                     dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@global_router.delete("/mirror", tags=["Management"], include_in_schema=True,
                      dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@fujian_router.delete("/mirror", tags=["Management"], include_in_schema=True,
                      dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
async def delete_mirror_url(response: Response, request: Request,
                            delete_request: MirrorDeleteModel) -> StandardResponse:
    """
    ## Delete Mirror URL

    Deletes a mirror URL for a specified project. If mirror_name is "all", clears the mirror list.
    
    **Restrictions:**
    - The project must be one of the predefined VALID_PROJECT_KEYS.
    - Returns HTTP 400 for invalid requests.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    project_key = delete_request.project_name
    mirror_name = delete_request.mirror_name
    current_version = await redis_client.get(f"{project_key}:version")
    current_version = current_version.decode("utf-8")
    project_mirror_redis_key = f"{project_key}:mirrors:{current_version}"

    if not mirror_name or project_key not in VALID_PROJECT_KEYS:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return StandardResponse(message="Invalid request")

    try:
        mirror_list = json.loads(await redis_client.get(project_mirror_redis_key))
    except TypeError:
        mirror_list = []
    current_mirror_names = [m["mirror_name"] for m in mirror_list]
    if mirror_name in current_mirror_names:
        method = "deleted"
        # Remove the url
        for m in mirror_list:
            if m["mirror_name"] == mirror_name:
                mirror_list.remove(m)
    elif mirror_name == "all":
        method = "cleared"
        mirror_list = []
    else:
        method = "not found"
    logger.info(f"{method.capitalize()} {mirror_name} mirror URL for {project_key}")

    # Overwrite mirror link to Redis
    update_result = await redis_client.set(project_mirror_redis_key, json.dumps(mirror_list, default=pydantic_encoder))
    logger.info(f"Set {project_mirror_redis_key} to Redis: {update_result}")

    # Refresh project patch
    if project_key == "snap-hutao":
        await update_snap_hutao_latest_version(redis_client)
    elif project_key == "snap-hutao-deployment":
        await update_snap_hutao_deployment_version(redis_client)
    response.status_code = status.HTTP_201_CREATED
    logger.info(f"Latest overwritten URL data: {mirror_list}")
    return StandardResponse(message=f"Successfully {method} {mirror_name} mirror URL for {project_key}",
                            data=mirror_list)


@china_router.get("/mirror", tags=["Management"], include_in_schema=True,
                  dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@global_router.get("/mirror", tags=["Management"], include_in_schema=True,
                   dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
@fujian_router.get("/mirror", tags=["Management"], include_in_schema=True,
                   dependencies=[Depends(verify_api_token)], response_model=StandardResponse)
async def get_mirror_url(request: Request, project: str) -> StandardResponse:
    """
    ## Get Overridden Mirror URLs

    Returns the list of overridden mirror URLs for the specified project from Redis.
    
    **Restrictions:**
    - The project must be a valid project key.
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    if project not in VALID_PROJECT_KEYS:
        return StandardResponse(message="Invalid request")
    current_version = await redis_client.get(f"{project}:version")
    project_mirror_redis_key = f"{project}:mirrors:{current_version}"

    try:
        mirror_list = json.loads(await redis_client.get(project_mirror_redis_key))
    except TypeError:
        mirror_list = []
    return StandardResponse(message=f"Overwritten URL data for {project}",
                            data=mirror_list)
