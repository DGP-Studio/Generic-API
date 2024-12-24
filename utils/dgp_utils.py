import json
import logging
import os
import httpx
from fastapi import HTTPException, status, Header, Request
from redis import asyncio as aioredis
import redis
from typing import Annotated
from base_logger import logger
from config import github_headers

try:
    WHITE_LIST_REPOSITORIES = json.loads(os.environ.get("WHITE_LIST_REPOSITORIES", "{}"))
except json.JSONDecodeError:
    WHITE_LIST_REPOSITORIES = {}
    logger.error("Failed to load WHITE_LIST_REPOSITORIES from environment variable.")
    logger.info(os.environ.get("WHITE_LIST_REPOSITORIES"))
BYPASS_CLIENT_VERIFICATION = os.environ.get("BYPASS_CLIENT_VERIFICATION", "False").lower() == "true"
if BYPASS_CLIENT_VERIFICATION:
    logger.warning("Client verification is bypassed in this server.")


def update_recent_versions() -> list[str]:
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    redis_conn = redis.Redis(host=REDIS_HOST, port=6379, db=0)
    new_user_agents = []

    # Stable version of software in white list
    for k, v in WHITE_LIST_REPOSITORIES.items():
        this_repo_headers = []
        this_page = 1
        latest_version = httpx.get(f"https://api.github.com/repos/{k}/releases/latest",
                                   headers=github_headers).json()["tag_name"]
        this_repo_headers.append(v.format(ver=latest_version))

        while len(this_repo_headers) < 4:
            all_versions = httpx.get(f"https://api.github.com/repos/{k}/releases?per_page=30&page={this_page}",
                                     headers=github_headers).json()
            stable_versions = [v.format(ver=r["tag_name"]) for r in all_versions if not r["prerelease"]][:4]
            this_repo_headers += stable_versions
            this_page += 1
        this_repo_headers = list(set(this_repo_headers))[:4]

        # Guessing next version
        latest_version_int_list = [int(i) for i in latest_version.split(".")]
        next_major_version = f"{latest_version_int_list[0] + 1}.0.0"
        next_minor_version = f"{latest_version_int_list[0]}.{latest_version_int_list[1] + 1}.0"
        next_patch_version = f"{latest_version_int_list[0]}.{latest_version_int_list[1]}.{latest_version_int_list[2] + 1}"
        this_repo_headers.append(v.format(ver=next_major_version))
        this_repo_headers.append(v.format(ver=next_minor_version))
        this_repo_headers.append(v.format(ver=next_patch_version))

        this_repo_headers = list(set(this_repo_headers))
        new_user_agents += this_repo_headers

    # Snap Hutao Alpha
    snap_hutao_alpha_patch_meta = redis_conn.get("snap-hutao-alpha:patch").json()
    if snap_hutao_alpha_patch_meta:
        snap_hutao_alpha_patch_version = snap_hutao_alpha_patch_meta["version"]
        new_user_agents.append(f"Snap Hutao/{snap_hutao_alpha_patch_version}")

    # Snap Hutao Next Version
    pr_list = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao.Docs/pulls",
                        headers=github_headers).json()
    all_opened_pr_title = [pr["title"] for pr in pr_list if
                           pr["state"] == "open" and pr["title"].startswith("Update to ")]
    if len(all_opened_pr_title) > 0:
        next_version = all_opened_pr_title[0].split(" ")[2] + ".0"
        new_user_agents.append(f"Snap Hutao/{next_version}")

    redis_resp = redis_conn.set("allowed_user_agents", json.dumps(new_user_agents), ex=5 * 60)
    logging.info(f"Updated allowed user agents: {new_user_agents}. Result: {redis_resp}")
    return new_user_agents


async def validate_client_is_updated(request: Request, user_agent: Annotated[str, Header()]) -> bool:
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    if BYPASS_CLIENT_VERIFICATION:
        return True
    logger.info(f"Received request from user agent: {user_agent}")
    if user_agent.startswith("Snap Hutao/2024"):
        return True
    if user_agent.startswith("PaimonsNotebook/"):
        return True

    allowed_user_agents = await redis_client.get("allowed_user_agents")
    if allowed_user_agents:
        allowed_user_agents = json.loads(allowed_user_agents)
    else:
        # redis data is expired
        logger.info("Updating allowed user agents from GitHub")
        allowed_user_agents = update_recent_versions()

    if user_agent not in allowed_user_agents:
        logger.info(f"Client is outdated: {user_agent}, not in the allowed list: {allowed_user_agents}")
        raise HTTPException(status_code=status.HTTP_418_IM_A_TEAPOT, detail="Client is outdated.")
    return True
