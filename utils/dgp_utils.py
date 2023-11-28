import json
import logging
import os
import httpx
from fastapi_utils.tasks import repeat_every
from fastapi import HTTPException, status, Header
from typing import Annotated
from base_logger import logger

WHITE_LIST_REPOSITORIES = json.loads(os.environ.get("WHITE_LIST_REPOSITORIES"))


def update_recent_versions():
    new_user_agents = []

    # Stable version of software in white list
    for k, v in WHITE_LIST_REPOSITORIES.items():
        this_repo_headers = []
        this_page = 1
        latest_version = httpx.get(f"https://api.github.com/repos/{k}/releases/latest").json()["tag_name"]
        this_repo_headers.append(v.format(ver=latest_version))
        while len(this_repo_headers) < 2:
            all_versions = httpx.get(f"https://api.github.com/repos/{k}/releases?per_page=30&page={this_page}").json()
            stable_versions = [v.format(ver=r["tag_name"]) for r in all_versions if not r["prerelease"]][:2]
            this_repo_headers += stable_versions
            this_repo_headers = list(set(this_repo_headers))
            this_page += 1
        new_user_agents += this_repo_headers[:2]

    # Snap Hutao Alpha
    hutao_alpha_list = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao/releases").json()
    pre_release_versions = [v["tag_name"] for v in hutao_alpha_list if v["prerelease"]][:5]
    new_user_agents += [f"Snap Hutao/{v}" for v in pre_release_versions]

    logging.info(f"Updated allowed user agents: {new_user_agents}")
    return new_user_agents


allowed_user_agents = update_recent_versions()


@repeat_every(seconds=5 * 60)
def timely_update_allowed_ua():
    global allowed_user_agents
    allowed_user_agents = update_recent_versions()


async def validate_client_is_updated(user_agent: Annotated[str, Header()]):
    logger.info(f"Received request from user agent: {user_agent}")
    if user_agent.startswith("Snap Hutao/2023"):
        return True
    if user_agent not in allowed_user_agents:
        logger.info(f"Client is outdated: {user_agent}, not in the allowed list: {allowed_user_agents}")
        raise HTTPException(status_code=status.HTTP_418_IM_A_TEAPOT, detail="Client is outdated.")
    return True
