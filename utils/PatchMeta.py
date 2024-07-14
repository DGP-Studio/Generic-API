from pydantic import BaseModel
from datetime import datetime


class MirrorMeta(BaseModel):
    url: str
    mirror_name: str

    def __str__(self):
        return f"MirrorMeta(url={self.url}, mirror_name={self.mirror_name})"


class PatchMeta(BaseModel):
    version: str
    validation: str
    cache_time: datetime
    mirrors: list[MirrorMeta] = []

    def __str__(self):
        return f"PatchMeta(version={self.version}, validation={self.validation}, cache_time={self.cache_time}, mirrors={self.mirrors})"
