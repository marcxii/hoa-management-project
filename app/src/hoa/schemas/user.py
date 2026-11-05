import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from hoa.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole
    resident_id: uuid.UUID | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    resident_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
