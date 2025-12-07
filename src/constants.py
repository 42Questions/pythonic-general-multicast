
from typing import Final
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    REPAIR_CACHE_SIZE: Final[int] = Field(alias="REPAIR_CACHE_SIZE", default=100, frozen=True)
    NAK_AGGREGATION_INTERVAL: Final[float] = Field(alias="NAK_AGGREGATION_INTERVAL", default=0.01, frozen=True) 
