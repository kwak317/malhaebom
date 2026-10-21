from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class NcsCompetencyOption(BaseModel):
    id: str
    category: Literal["knowledge", "skill", "attitude"]
    label: str
    ncs_unit_code: str
    ncs_unit_name: str


class NcsBackendCompetenciesResponse(BaseModel):
    data_source: Literal["live", "cached"] = "live"
    fetched_at: datetime | None = None
    job_name: str
    source_url: str
    options: list[NcsCompetencyOption]
