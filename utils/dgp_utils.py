import json
import os
import httpx
from fastapi_utils.tasks import repeat_every
from fastapi import HTTPException, status, Header
from typing import Annotated

WHITE_LIST_REPOSITORIES = json.loads(os.environ.get("WHITE_LIST_REPOSITORIES"))


def update_recent_versions():
    new_user_agents = []
    for k, v in WHITE_LIST_REPOSITORIES.items():
        this_repo_headers = []
        this_page = 1
        while len(this_repo_headers) < 2:
            all_versions = httpx.get(f"https://api.github.com/repos/{k}/releases?per_page=30&page={this_page}").json()
            stable_versions = [v.format(ver=r["tag_name"]) for r in all_versions if not r["prerelease"]][:2]
            this_repo_headers += stable_versions
            this_page += 1
        new_user_agents += this_repo_headers[:2]
    print(f"Updated allowed user agents: {new_user_agents}")
    return new_user_agents


allowed_user_agents = update_recent_versions()


@repeat_every(seconds=5 * 60)
def timely_update_allowed_ua():
    global allowed_user_agents
    allowed_user_agents = update_recent_versions()


async def validate_client_is_updated(user_agent: Annotated[str, Header()]):
    if user_agent not in allowed_user_agents:
        raise HTTPException(status_code=status.HTTP_418_IM_A_TEAPOT, detail="Client is outdated.")
    return True
