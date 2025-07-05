import json
import os
import httpx
from base_logger import get_logger
from config import github_headers, IS_DEBUG

logger = get_logger(__name__)
try:
    WHITE_LIST_REPOSITORIES = json.loads(os.environ.get("WHITE_LIST_REPOSITORIES", "{}"))
except json.JSONDecodeError:
    WHITE_LIST_REPOSITORIES = {}
    logger.error("Failed to load WHITE_LIST_REPOSITORIES from environment variable.")
    logger.info(os.environ.get("WHITE_LIST_REPOSITORIES"))

# Helper: HTTP GET with retry
async def fetch_with_retry(url, max_retries=3):
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(url, headers=github_headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{max_retries} failed for {url}: {e}")
    logger.error(f"All {max_retries} attempts failed for {url}")
    return None

# Static preset values for fallback
STATIC_PRESET_VERSIONS = ["Snap.Hutao", "PaimonsNotebook"]

async def update_recent_versions(redis_client) -> list[str]:
    new_user_agents = []
    
    # Process WHITE_LIST_REPOSITORIES with retry and fallback static preset values
    for k, v in WHITE_LIST_REPOSITORIES.items():
        this_repo_headers = []
        this_page = 1
        latest_release = await fetch_with_retry(f"https://api.github.com/repos/{k}/releases/latest")
        if latest_release is None:
            logger.warning(f"Failed to fetch latest release for {k}; using static preset values.")
            new_user_agents += STATIC_PRESET_VERSIONS
            continue
        latest_version = latest_release.get("tag_name")
        this_repo_headers.append(v.format(ver=latest_version))
        
        while len(this_repo_headers) < 4:
            all_versions = await fetch_with_retry(f"https://api.github.com/repos/{k}/releases?per_page=30&page={this_page}")
            if all_versions is None:
                logger.warning(f"Failed to fetch releases for {k}; using static preset values.")
                new_user_agents += STATIC_PRESET_VERSIONS
                break
            stable_versions = [v.format(ver=r["tag_name"]) for r in all_versions if not r.get("prerelease", False)]
            this_repo_headers += stable_versions[:4 - len(this_repo_headers)]
            this_page += 1
        this_repo_headers = list(set(this_repo_headers))[:4]
        
        # Guessing next version
        try:
            latest_version_int_list = [int(i) for i in latest_version.split(".")]
            next_major_version = f"{latest_version_int_list[0]+1}.0.0"
            next_minor_version = f"{latest_version_int_list[0]}.{latest_version_int_list[1]+1}.0"
            next_patch_version = f"{latest_version_int_list[0]}.{latest_version_int_list[1]}.{latest_version_int_list[2]+1}"
        except Exception as e:
            logger.error(f"Failed to parse version '{latest_version}' for {k}: {e}")
            next_major_version = next_minor_version = next_patch_version = latest_version
        
        this_repo_headers.append(v.format(ver=next_major_version))
        this_repo_headers.append(v.format(ver=next_minor_version))
        this_repo_headers.append(v.format(ver=next_patch_version))
        this_repo_headers = list(set(this_repo_headers))
        new_user_agents += this_repo_headers

    # Snap Hutao Alpha
    snap_hutao_alpha_patch_meta = await redis_client.get("snap-hutao-alpha:patch")
    if snap_hutao_alpha_patch_meta:
        snap_hutao_alpha_patch_meta = snap_hutao_alpha_patch_meta.decode("utf-8")
        snap_hutao_alpha_patch_meta = json.loads(snap_hutao_alpha_patch_meta)
        snap_hutao_alpha_patch_version = snap_hutao_alpha_patch_meta["version"]
        new_user_agents.append(f"Snap Hutao/{snap_hutao_alpha_patch_version}")

    # Snap Hutao Next Version with retry; ignore if fails
    pr_list = await fetch_with_retry("https://api.github.com/repos/DGP-Studio/Snap.Hutao.Docs/pulls")
    if pr_list is not None and len(pr_list) > 0:
        all_opened_pr_title = [pr["title"] for pr in pr_list if pr.get("state") == "open" and pr["title"].startswith("Update to ")]
        if all_opened_pr_title:
            next_version = all_opened_pr_title[0].split(" ")[2] + ".0"
            new_user_agents.append(f"Snap Hutao/{next_version}")
    else:
        logger.warning("Failed to fetch PR information; ignoring PR update.")

    # Remove duplicates and sort
    new_user_agents = list(set(new_user_agents))

    redis_resp = await redis_client.set("allowed_user_agents", json.dumps(new_user_agents), ex=60*60)
    logger.info(f"Updated allowed user agents: {new_user_agents}. Result: {redis_resp}")
    return new_user_agents


