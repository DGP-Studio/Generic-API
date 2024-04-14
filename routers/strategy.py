import json
import httpx
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from utils.uigf import get_genshin_avatar_id
from utils.redis_utils import redis_conn
from utils.authentication import verify_api_token
from mysql_app.database import SessionLocal
from mysql_app.schemas import AvatarStrategy, StandardResponse
from mysql_app.crud import add_avatar_strategy, get_all_avatar_strategy, get_avatar_strategy_by_id

china_router = APIRouter(tags=["Strategy"], prefix="/strategy")
global_router = APIRouter(tags=["Strategy"], prefix="/strategy")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def refresh_miyoushe_avatar_strategy(db: Session = None) -> bool:
    """
    Refresh avatar strategy from Miyoushe
    :param db: Database session
    :return: True if successful else raise RuntimeError
    """
    if not db:
        db = SessionLocal()
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
                        avatar_id = get_genshin_avatar_id(avatar["name"], "chs")
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


def refresh_hoyolab_avatar_strategy(db: Session = None) -> bool:
    """
    Refresh avatar strategy from Hoyolab
    :param db: Database session
    :return: true if successful else raise RuntimeError
    """
    avatar_strategy = []
    if not db:
        db = SessionLocal()
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
        avatar_id = get_genshin_avatar_id(item["title"], "chs")
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
def refresh_avatar_strategy(channel: str, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Refresh avatar strategy from Miyoushe or Hoyolab
    :param channel: one of `miyoushe`, `hoyolab`, `all`
    :param db: Database session
    :return: StandardResponse with DB operation result and full cached strategy dict
    """
    if channel == "miyoushe":
        result = {"mys": refresh_miyoushe_avatar_strategy(db)}
    elif channel == "hoyolab":
        result = {"hoyolab": refresh_hoyolab_avatar_strategy(db)}
    elif channel == "all":
        result = {"mys": refresh_miyoushe_avatar_strategy(db),
                  "hoyolab": refresh_hoyolab_avatar_strategy(db)
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
    if redis_conn:
        redis_conn.set("avatar_strategy", json.dumps(strategy_dict))

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
def get_avatar_strategy_item(item_id: int, db: Session = Depends(get_db)) -> StandardResponse:
    """
    Get avatar strategy item by avatar ID
    :param item_id: Genshin internal avatar ID (compatible with weapon id if available)
    :param db: Database session
    :return: strategy URLs for Miyoushe and Hoyolab
    """
    MIYOUSHE_STRATEGY_URL = "https://bbs.mihoyo.com/ys/strategy/channel/map/39/{mys_strategy_id}?bbs_presentation_style=no_header"
    HOYOLAB_STRATEGY_URL = "https://www.hoyolab.com/guidelist?game_id=2&guide_id={hoyolab_strategy_id}"

    if redis_conn:
        try:
            strategy_dict = json.loads(redis_conn.get("avatar_strategy"))
        except TypeError:
            refresh_avatar_strategy("all", db)
            strategy_dict = json.loads(redis_conn.get("avatar_strategy"))
        strategy_set = strategy_dict.get(str(item_id), {})
        if strategy_set:
            miyoushe_url = MIYOUSHE_STRATEGY_URL.format(mys_strategy_id=strategy_set.get("mys_strategy_id"))
            hoyolab_url = HOYOLAB_STRATEGY_URL.format(hoyolab_strategy_id=strategy_set.get("hoyolab_strategy_id"))
        else:
            miyoushe_url = None
            hoyolab_url = None
    else:
        result = get_avatar_strategy_by_id(avatar_id=str(item_id), db=db)
        if result:
            miyoushe_url = MIYOUSHE_STRATEGY_URL.format(mys_strategy_id=result.mys_strategy_id)
            hoyolab_url = HOYOLAB_STRATEGY_URL.format(hoyolab_strategy_id=result.hoyolab_strategy_id)
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
