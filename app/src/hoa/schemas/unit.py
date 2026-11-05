import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UnitBase(BaseModel):
    property_id: uuid.UUID
    unit_number: str
    square_feet: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    unit_number: str | None = None
    square_feet: int | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None


class UnitRead(UnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
