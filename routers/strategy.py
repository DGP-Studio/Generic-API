import json
import httpx
from fastapi import Depends, APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from utils.uigf import get_genshin_avatar_id
from redis import asyncio as redis
from utils.authentication import verify_api_token
from mysql_app.schemas import AvatarStrategy, StandardResponse
from mysql_app.crud import add_avatar_strategy, get_all_avatar_strategy, get_avatar_strategy_by_id


china_router = APIRouter(tags=["Strategy"], prefix="/strategy")
global_router = APIRouter(tags=["Strategy"], prefix="/strategy")
fujian_router = APIRouter(tags=["Strategy"], prefix="/strategy")


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
                        if avatar_id:
                            avatar_strategy.append(
                                AvatarStrategy(
                                    avatar_id=avatar_id,
                                    mys_strategy_id=avatar["id"]
                                )
                            )
                        else:
                            print(f"Failed to get avatar id for {avatar['name']}")
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


@china_router.get("/refresh", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@global_router.get("/refresh", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
@fujian_router.get("/refresh", response_model=StandardResponse, dependencies=[Depends(verify_api_token)])
async def refresh_avatar_strategy(request: Request, channel: str) -> StandardResponse:
    """
    Refresh avatar strategy from Miyoushe or Hoyolab
    :param request: request object from FastAPI
    :param channel: one of `miyoushe`, `hoyolab`, `all`
    :return: StandardResponse with DB operation result and full cached strategy dict
    """
    db = request.app.state.mysql
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    if channel == "miyoushe":
        result = {"mys": await refresh_miyoushe_avatar_strategy(redis_client, db)}
    elif channel == "hoyolab":
        result = {"hoyolab": await refresh_hoyolab_avatar_strategy(redis_client, db)}
    elif channel == "all":
        result = {"mys": await refresh_miyoushe_avatar_strategy(redis_client, db),
                  "hoyolab": await refresh_hoyolab_avatar_strategy(redis_client, db)
                  }
    else:
        raise HTTPException(status_code=400, detail="Invalid channel")

    all_strategies = get_all_avatar_strategy(db)
    strategy_dict = {}
    for strategy in all_strategies:
        strategy_dict[strategy.avatar_id] = {
            "mys_strategy_id": strategy.mys_strategy_id,
            "hoyolab_strategy_id": strategy.hoyolab_strategy_id
        }
    await redis_client.set("avatar_strategy", json.dumps(strategy_dict))

    return StandardResponse(
        retcode=0,
        message="Success",
        data={
            "db": result,
            "cache": strategy_dict
        }
    )


@china_router.get("/item", response_model=StandardResponse)
@global_router.get("/item", response_model=StandardResponse)
@fujian_router.get("/item", response_model=StandardResponse)
async def get_avatar_strategy_item(request: Request, item_id: int) -> StandardResponse:
    """
    Get avatar strategy item by avatar ID
    :param request: request object from FastAPI
    :param item_id: Genshin internal avatar ID (compatible with weapon id if available)
    :return: strategy URLs for Miyoushe and Hoyolab
    """
    miyoushe_strategy_url = "https://bbs.mihoyo.com/ys/strategy/channel/map/39/{mys_strategy_id}?bbs_presentation_style=no_header"
    hoyolab_strategy_url = "https://www.hoyolab.com/guidelist?game_id=2&guide_id={hoyolab_strategy_id}"
    redis_client = redis.Redis.from_pool(request.app.state.redis)
    db = request.app.state.mysql

    if redis_client:
        try:
            strategy_dict = json.loads(await redis_client.get("avatar_strategy"))
        except TypeError:
            await refresh_avatar_strategy(request, "all")
            strategy_dict = json.loads(await redis_client.get("avatar_strategy"))
        strategy_set = strategy_dict.get(str(item_id), {})
        if strategy_set:
            miyoushe_url = miyoushe_strategy_url.format(mys_strategy_id=strategy_set.get("mys_strategy_id"))
            hoyolab_url = hoyolab_strategy_url.format(hoyolab_strategy_id=strategy_set.get("hoyolab_strategy_id"))
        else:
            miyoushe_url = None
            hoyolab_url = None
    else:
        result = get_avatar_strategy_by_id(avatar_id=str(item_id), db=db)
        if result:
            miyoushe_url = miyoushe_strategy_url.format(mys_strategy_id=result.mys_strategy_id)
            hoyolab_url = hoyolab_strategy_url.format(hoyolab_strategy_id=result.hoyolab_strategy_id)
        else:
            miyoushe_url = None
            hoyolab_url = None
    res = StandardResponse(
        retcode=0,
        message="Success",
        data={
            "miyoushe_url": miyoushe_url,
            "hoyolab_url": hoyolab_url
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
    miyoushe_strategy_url = "https://bbs.mihoyo.com/ys/strategy/channel/map/39/{mys_strategy_id}?bbs_presentation_style=no_header"
    hoyolab_strategy_url = "https://www.hoyolab.com/guidelist?game_id=2&guide_id={hoyolab_strategy_id}"
    redis_client = redis.Redis.from_pool(request.app.state.redis)

    try:
        strategy_dict = json.loads(await redis_client.get("avatar_strategy"))
    except TypeError:
        await refresh_avatar_strategy(request, "all")
        strategy_dict = json.loads(await redis_client.get("avatar_strategy"))
    for key in strategy_dict:
        strategy_set = strategy_dict[key]
        strategy_set["miyoushe_url"] = miyoushe_strategy_url.format(mys_strategy_id=strategy_set.get("mys_strategy_id"))
        strategy_set["hoyolab_url"] = hoyolab_strategy_url.format(hoyolab_strategy_id=strategy_set.get("hoyolab_strategy_id"))
    return StandardResponse(
        retcode=0,
        message="Success",
        data=strategy_dict
    )
