import json
import httpx
from fastapi import Depends, APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from utils.uigf import get_genshin_avatar_id
from redis import asyncio as redis
from mysql_app.schemas import AvatarStrategy, StandardResponse
from mysql_app.crud import add_avatar_strategy, get_avatar_strategy_by_id
from utils.dependencies import get_db
from base_logger import get_logger


logger = get_logger("strategy")
china_router = APIRouter(tags=["Strategy"], prefix="/strategy")
global_router = APIRouter(tags=["Strategy"], prefix="/strategy")
fujian_router = APIRouter(tags=["Strategy"], prefix="/strategy")

"""
miyoushe_strategy_url = "https://bbs.mihoyo.com/ys/strategy/channel/map/39/{mys_strategy_id}?bbs_presentation_style=no_header"
hoyolab_strategy_url = "https://www.hoyolab.com/guidelist?game_id=2&guide_id={hoyolab_strategy_id}"
"""


async def refresh_miyoushe_avatar_strategy(redis_client: redis.client.Redis, db: Session) -> bool:
    """
    Refresh avatar strategy from Miyoushe

    :param redis_client: redis client object

    :param db: Database session

    :return: True if successful else raise RuntimeError
    """
    avatar_strategy = []
    url = "https://api-static.mihoyo.com/common/blackboard/ys_strategy/v1/home/content/list?app_sn=ys_strategy&channel_id=37"
    response = httpx.get(url)
    if response.status_code == 200:
        data = response.json().get("data", {}).get("list", [])
    else:
        raise RuntimeError(
            f"Failed to refresh Miyoushe avatar strategy, \nstatus code: {response.status_code}, \ncontent: {response.text}")
    for top_menu in data:
        if top_menu["id"] == 37:
            for item in top_menu["children"]:
                if item["id"] == 39:
                    for avatar in item["children"]:
                        avatar_id = await get_genshin_avatar_id(redis_client, avatar["name"], "chs")
                        logger.info(f"Processing avatar: {avatar['name']}, UIGF ID: {avatar_id}")
                        if avatar_id:
                            avatar_strategy.append(
                                AvatarStrategy(
                                    avatar_id=avatar_id,
                                    mys_strategy_id=avatar["id"]
                                )
                            )
                        else:
                            logger.error(f"Failed to get avatar id for {avatar['name']}")
                    break
    for strategy in avatar_strategy:
        mysql_add_result = add_avatar_strategy(db, strategy)
        if not mysql_add_result:
            raise RuntimeError(f"Failed to add avatar strategy to MySQL: {strategy}")
    db.close()
    return True


async def refresh_hoyolab_avatar_strategy(redis_client: redis.client.Redis, db: Session) -> bool:
    """
    Refresh avatar strategy from Hoyolab

    :param redis_client: redis client object

    :param db: Database session

    :return: true if successful else raise RuntimeError
    """
    avatar_strategy = []
    url = "https://bbs-api-os.hoyolab.com/community/painter/wapi/circle/channel/guide/second_page/info"
    response = httpx.post(url, json={
        "id": "63b63aefc61f3cbe3ead18d9",
        "offset": "",
        "selector_id_list": [],
        "size": 100
    }, headers={
        "Accept-Language": "zh-CN,zh;q=0.9",
        "X-Rpc-Language": "zh-cn",
        "X-Rpc-Show-Translated": "true"
    })
    if response.status_code == 200:
        data = response.json().get("data", {}).get("grid_item_list", [])
    else:
        raise RuntimeError(
            f"Failed to refresh Hoyolab avatar strategy, \nstatus code: {response.status_code}, \ncontent: {response.text}")
    for item in data:
        avatar_id = await get_genshin_avatar_id(redis_client, item["title"], "chs")
        logger.info(f"Processing avatar: {item['title']}, UIGF ID: {avatar_id}")
        if avatar_id:
            avatar_strategy.append(
                AvatarStrategy(
                    avatar_id=avatar_id,
                    hoyolab_strategy_id=item["id"]
                )
            )
    for strategy in avatar_strategy:
        mysql_add_result = add_avatar_strategy(db, strategy)
        if not mysql_add_result:
            raise RuntimeError(f"Failed to add avatar strategy to MySQL: {strategy}")
    db.close()
    return True


@china_router.get("/item", response_model=StandardResponse)
@global_router.get("/item", response_model=StandardResponse)
@fujian_router.get("/item", response_model=StandardResponse)
async def get_avatar_strategy_item(request: Request, item_id: int, db: Session=Depends(get_db)) -> StandardResponse:
    """
    Get avatar strategy item by avatar ID

    :param request: request object from FastAPI

    :param item_id: Genshin internal avatar ID (compatible with weapon id if available)

    :param db: Database session

    :return: strategy URLs for Miyoushe and Hoyolab
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)

    if redis_client:
        try:
            strategy_dict = json.loads(await redis_client.get("avatar_strategy"))
        except TypeError:
            from cloudflare_security_utils.mgnt import refresh_avatar_strategy
            await refresh_avatar_strategy(request, "all")
            strategy_dict = json.loads(await redis_client.get("avatar_strategy"))
        strategy_set = strategy_dict.get(str(item_id), {})
        if strategy_set:
            miyoushe_id = strategy_set.get("mys_strategy_id")
            hoyolab_id = strategy_set.get("hoyolab_strategy_id")
        else:
            miyoushe_id = None
            hoyolab_id = None
    else:
        result = get_avatar_strategy_by_id(avatar_id=str(item_id), db=db)
        if result:
            miyoushe_id = result.mys_strategy_id
            hoyolab_id = result.hoyolab_strategy_id
        else:
            miyoushe_id = None
            hoyolab_id = None
    res = StandardResponse(
        retcode=0,
        message="Success",
        data={
            item_id: {
                "mys_strategy_id": miyoushe_id,
                "hoyolab_strategy_id": hoyolab_id
            }
        }
    )
    return res


@china_router.get("/all", response_model=StandardResponse)
@global_router.get("/all", response_model=StandardResponse)
@fujian_router.get("/all", response_model=StandardResponse)
async def get_all_avatar_strategy_item(request: Request) -> StandardResponse:
    """
    Get all avatar strategy items

    :param request: request object from FastAPI

    :return: all avatar strategy items
    """
    redis_client = redis.Redis.from_pool(request.app.state.redis)

    try:
        strategy_dict = json.loads(await redis_client.get("avatar_strategy"))
    except TypeError:
        from cloudflare_security_utils.mgnt import refresh_avatar_strategy
        await refresh_avatar_strategy(request, "all")
        strategy_dict = json.loads(await redis_client.get("avatar_strategy"))
    return StandardResponse(
        retcode=0,
        message="Success",
        data=strategy_dict
    )
