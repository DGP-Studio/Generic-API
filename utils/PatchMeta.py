from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class MirrorMeta(BaseModel):
    url: str
    mirror_name: str
    mirror_type: Literal["direct", "archive"] = "direct"

    def __str__(self):
        return f"MirrorMeta(url={self.url}, mirror_name={self.mirror_name}, mirror_type={self.mirror_type})"


class PatchMeta(BaseModel):
    version: str
    validation: str
    cache_time: datetime
    mirrors: list[MirrorMeta] = []

    def __str__(self):
        return f"PatchMeta(version={self.version}, validation={self.validation}, cache_time={self.cache_time}, mirrors={self.mirrors})"
