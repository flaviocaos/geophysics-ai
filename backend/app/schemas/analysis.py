from pydantic import BaseModel


class BouguerAnomalyRequest(BaseModel):
    station_id: str
    density_kg_m3: float = 2670.0


class MagneticRtpRequest(BaseModel):
    grid: list[list[float]]
    pixel_size_m: float
    inclination_deg: float
    declination_deg: float
    inclination_magnetization_deg: float | None = None
    declination_magnetization_deg: float | None = None


class ResistivitySoundingRequest(BaseModel):
    sounding_id: str


class SeismicRefractionRequest(BaseModel):
    line_id: str


class AnomalyDetectionRequest(BaseModel):
    grid: list[list[float]]
    threshold_sigma: float = 2.0
    direction: str = "both"
    pixel_size_m: float = 1.0
