from pydantic import BaseModel
from typing import Optional, Literal
import datetime


class StandardResponse(BaseModel):
    retcode: int = 0
    message: str = "ok"
    data: Optional[dict | list | None] = None


class ClientErrorMessageResponse(BaseModel):
    message: str = "Generic Server Error"


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


class GitRepositoryBase(BaseModel):
    name: str
    region: Literal["cn", "global"]
    web_url: str
    https_url: Optional[str] = None
    ssh_url: Optional[str] = None
    type: Optional[str] = None
    token: Optional[str] = None
    username: Optional[str] = None


class GitRepositoryCreate(GitRepositoryBase):
    pass


class GitRepositoryUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[Literal["cn", "global"]] = None
    web_url: Optional[str] = None
    https_url: Optional[str] = None
    ssh_url: Optional[str] = None
    type: Optional[str] = None
    token: Optional[str] = None
    username: Optional[str] = None


class GitRepository(GitRepositoryBase):
    id: int

    class Config:
        from_attributes = True
