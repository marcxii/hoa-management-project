import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from hoa.models.invoice import InvoiceStatus


class InvoiceBase(BaseModel):
    unit_id: uuid.UUID
    amount_cents: int
    due_date: date
    period_start: date
    period_end: date


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    amount_cents: int | None = None
    due_date: date | None = None
    status: InvoiceStatus | None = None


class InvoiceRead(InvoiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: InvoiceStatus
    created_at: datetime
