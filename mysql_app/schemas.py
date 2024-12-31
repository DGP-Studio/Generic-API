from pydantic import BaseModel
from typing import Optional
import datetime


class StandardResponse(BaseModel):
    retcode: int = 0
    message: str = "ok"
    data: Optional[dict | list | None] = None


class Wallpaper(BaseModel):
    url: str
    display_date: Optional[datetime.date | None] = None
    last_display_date: Optional[datetime.date | None] = None
    source_url: str
    author: str
    uploader: str
    disabled: Optional[int | bool] = False

    class Config:
        from_attributes = True

    def __repr__(self):
        return f"schema.Wallpaper({self.model_dump()})"


class RedemptionCode(BaseModel):
    code: str
    value: int
    used: Optional[bool] = False
    description: str
    created_by: str
    created_datetime: datetime.datetime
    used_by: Optional[str] = None
    used_datetime: Optional[datetime.datetime | None] = None


class RedemptionToken(BaseModel):
    token: str
    authority: str


class AvatarStrategy(BaseModel):
    avatar_id: int
    mys_strategy_id: Optional[int | None] = None
    hoyolab_strategy_id: Optional[int | None] = None

    class Config:
        from_attributes = True


class DailyActiveUserStats(BaseModel):
    date: datetime.date
    cn_user: int
    global_user: int
    unknown: int

    class Config:
        from_attributes = True


class DailyEmailSentStats(BaseModel):
    date: datetime.date
    requested: int
    sent: int
    failed: int

    class Config:
        from_attributes = True


class PatchMetadata(BaseModel):
    version: str
    release_date: datetime.date
    description: str
    download_url: str
    patch_notes: str
    disabled: Optional[bool] = False

    class Config:
        from_attributes = True
