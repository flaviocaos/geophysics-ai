from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SurveyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    boundary: dict  # GeoJSON Polygon
    survey_type: str = "multi-metodo"


class SurveyRead(BaseModel):
    id: UUID
    name: str
    survey_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GravityStationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    lon: float
    lat: float
    latitude_deg: float
    elevation_m: float
    observed_gravity_mgal: float


class ResistivitySoundingCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    lon: float
    lat: float
    array_type: str = "wenner"


class ResistivityReadingCreate(BaseModel):
    voltage_v: float
    current_ma: float
    spacing_m: float | None = None
    current_spacing_m: float | None = None
    potential_spacing_m: float | None = None


class SeismicLineCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    coordinates: list[list[float]]  # [[lon,lat], ...] LineString


class SeismicReadingCreate(BaseModel):
    offset_m: float
    first_arrival_time_ms: float
    is_direct_wave: bool | None = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict]
