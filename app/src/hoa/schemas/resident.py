import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ResidentBase(BaseModel):
    unit_id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    is_owner: bool = False
    move_in_date: date | None = None
    move_out_date: date | None = None


class ResidentCreate(ResidentBase):
    pass


class ResidentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    is_owner: bool | None = None
    move_in_date: date | None = None
    move_out_date: date | None = None


class ResidentRead(ResidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
