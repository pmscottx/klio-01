from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class InspectionCreate(BaseModel):
    image_count: int = 0


class InspectionPatch(BaseModel):
    status: str | None = None
    licenceplate: str | None = None
    licenceplate_status: str | None = None
    licenceplate_desc: str | None = None
    vin: str | None = None
    vin_status: str | None = None
    vin_car: str | None = None
    vin_production_year: date | None = None


class InspectionOut(BaseModel):
    id: str
    status: str
    image_count: int
    licenceplate: str | None
    licenceplate_status: str | None
    licenceplate_desc: str | None
    vin: str | None
    vin_status: str | None
    vin_car: str | None
    vin_production_year: date | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
