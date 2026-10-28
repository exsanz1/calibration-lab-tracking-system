from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200))
    pic_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(100), default=None)
    address: Mapped[str | None] = mapped_column(String(500), default=None)

    orders: Mapped[list[Order]] = relationship(back_populates="customer")
