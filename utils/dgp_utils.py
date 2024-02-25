import json
import logging
import os
import httpx
from fastapi_utils.tasks import repeat_every
from fastapi import HTTPException, status, Header
from typing import Annotated
from base_logger import logger
from config import github_headers

WHITE_LIST_REPOSITORIES = json.loads(os.environ.get("WHITE_LIST_REPOSITORIES"))
BYPASS_CLIENT_VERIFICATION = os.environ.get("BYPASS_CLIENT_VERIFICATION", "False").lower() == "true"
if BYPASS_CLIENT_VERIFICATION:
    logger.warning("Client verification is bypassed in this server.")


def update_recent_versions():
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
    # To be redesigned

    # Snap Hutao Next Version
    pr_list = httpx.get("https://api.github.com/repos/DGP-Studio/Snap.Hutao.Docs/pulls",
                        headers=github_headers).json()
    all_opened_pr_title = [pr["title"] for pr in pr_list if
                           pr["state"] == "open" and pr["title"].startswith("Update to ")]
    if len(all_opened_pr_title) > 0:
        next_version = all_opened_pr_title[0].split(" ")[2] + ".0"
        new_user_agents.append(f"Snap Hutao/{next_version}")

    logging.info(f"Updated allowed user agents: {new_user_agents}")
    return new_user_agents


allowed_user_agents = update_recent_versions()


@repeat_every(seconds=5 * 60)
def timely_update_allowed_ua():
    global allowed_user_agents
    allowed_user_agents = update_recent_versions()


async def validate_client_is_updated(user_agent: Annotated[str, Header()]):
    if BYPASS_CLIENT_VERIFICATION:
        return True
    logger.info(f"Received request from user agent: {user_agent}")
    if user_agent.startswith("Snap Hutao/2024"):
        return True
    if user_agent.startswith("PaimonsNotebook/"):
        return True
    if user_agent not in allowed_user_agents:
        logger.info(f"Client is outdated: {user_agent}, not in the allowed list: {allowed_user_agents}")
        raise HTTPException(status_code=status.HTTP_418_IM_A_TEAPOT, detail="Client is outdated.")
    return True
