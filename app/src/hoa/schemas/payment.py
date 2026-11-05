import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from hoa.models.payment import PaymentMethod


class PaymentBase(BaseModel):
    invoice_id: uuid.UUID
    amount_cents: int
    paid_at: datetime
    method: PaymentMethod
    reference: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
