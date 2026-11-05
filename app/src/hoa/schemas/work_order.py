import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from hoa.models.work_order import WorkOrderPriority, WorkOrderStatus


class WorkOrderBase(BaseModel):
    unit_id: uuid.UUID
    title: str
    description: str | None = None
    priority: WorkOrderPriority = WorkOrderPriority.medium


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: WorkOrderPriority | None = None
    status: WorkOrderStatus | None = None
    assigned_to: str | None = None


class WorkOrderRead(WorkOrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: WorkOrderStatus
    assigned_to: str | None
    requested_by_resident_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
