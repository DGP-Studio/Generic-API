import httpx
import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Request
from redis import asyncio as aioredis
from mysql_app.schemas import StandardResponse
from utils.stats import record_device_id
from base_logger import get_logger
from config import github_headers

logger = get_logger(__name__)

china_router = APIRouter(tags=["Issue"], prefix="/issue")
global_router = APIRouter(tags=["Issue"], prefix="/issue")
fujian_router = APIRouter(tags=["Issue"], prefix="/issue")

GITHUB_ISSUES_URL = "https://api.github.com/repos/DGP-Studio/Snap.Hutao/issues"
CACHE_KEY = "issues:hutao:open:bug"
CACHE_TTL_SECONDS = 600


def _prune_issue_fields(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only required fields and drop PRs."""
    issues_only = [i for i in items if "pull_request" not in i]
    return [
        {
            "number": i.get("number"),
            "title": i.get("title"),
            "labels": [l.get("name") for l in i.get("labels", [])],
            "author": (i.get("user") or {}).get("login", ""),
            "created_at": i.get("created_at"),
        }
        for i in issues_only
    ]


def _fetch_open_bug_issues() -> List[Dict[str, Any]]:
    """Fetch open issues labeled 'Bug' from GitHub."""
    params = {
        "state": "open",
        "type": "Bug"
    }
    logger.debug(f"Fetching issues from GitHub: {GITHUB_ISSUES_URL} {params}")
    resp = httpx.get(GITHUB_ISSUES_URL, headers=github_headers, params=params, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    pruned = _prune_issue_fields(data)
    logger.info(f"Fetched {len(pruned)} open 'Bug' issues")
    return pruned


def _calc_bug_stats(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate bug stats based on label rules."""
    stat = {
        "waiting_for_release": 0,
        "untreated": 0,
        "hard_to_fix": 0,
    }
    for issue in issues:
        labels = [l for l in issue.get("labels", []) if not l.startswith("priority")]
        # 1. 包含 "等待发布" 代表问题已修复但等待发布
        if "等待发布" in labels:
            stat["waiting_for_release"] += 1
        # 2. 只包含 area 开头的 label 代表未处理
        area_labels = [l for l in labels if l.startswith("area")]
        if area_labels and len(area_labels) == len(labels):
            stat["untreated"] += 1
        # 3. need-community-help 或 无法稳定复现 代表难以修复
        if any(l in labels for l in ["need-community-help", "无法稳定复现"]):
            stat["hard_to_fix"] += 1
    return stat


@china_router.get("/bug", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
@global_router.get("/bug", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
@fujian_router.get("/bug", response_model=StandardResponse, dependencies=[Depends(record_device_id)])
async def get_open_bug_issues(request: Request) -> StandardResponse:
    """Return open 'Bug' issues"""
    redis_client: aioredis.client.Redis = aioredis.Redis.from_pool(request.app.state.redis)

    # Try cache first
    cached = await redis_client.get(CACHE_KEY)
    if cached:
        try:
            data = json.loads(cached)
            return StandardResponse(retcode=0, message="From cache", data=data)
        except Exception as e:
            logger.warning(f"Failed to decode cached issues: {e}")

    # Fetch from GitHub and cache
    try:
        issues = _fetch_open_bug_issues()
        stat = _calc_bug_stats(issues)
        data = {"details": issues, "stat": stat}
        await redis_client.set(CACHE_KEY, json.dumps(data, ensure_ascii=False), ex=CACHE_TTL_SECONDS)
        return StandardResponse(retcode=0, message="Fetched from GitHub", data=data)
    except httpx.HTTPError as e:
        logger.error(f"GitHub API error: {e}")
        return StandardResponse(
            retcode=1,
            message="Failed to fetch issues",
            data={
                "details": [],
                "stat": {"waiting_for_release": 0, "untreated": 0, "hard_to_fix": 0}
            }
        )
