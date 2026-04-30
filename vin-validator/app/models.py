from datetime import date
from sqlalchemy import String, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Vin(Base):
    __tablename__ = "VIN"

    vin: Mapped[str] = mapped_column(String, primary_key=True)
    car: Mapped[str] = mapped_column(String)
    production_year: Mapped[date] = mapped_column(Date)
