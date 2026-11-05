import enum
import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from hoa.db.base import Base, TenantScopedMixin, TimestampMixin


class UserRole(enum.StrEnum):
    admin = "admin"
    board_member = "board_member"
    resident = "resident"


class User(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=True), nullable=False
    )
    # Only set for role == resident; links the login identity to the
    # resident/unit record so we know which unit's data they're allowed to see.
    resident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("residents.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
