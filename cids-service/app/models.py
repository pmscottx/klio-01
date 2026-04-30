from datetime import datetime, date
from sqlalchemy import String, Integer, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    licenceplate: Mapped[str | None] = mapped_column(String, nullable=True)
    licenceplate_status: Mapped[str | None] = mapped_column(String, nullable=True)
    licenceplate_desc: Mapped[str | None] = mapped_column(String, nullable=True)
    vin: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_status: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_car: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_production_year: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
