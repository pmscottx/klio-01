from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Box(Base):
    __tablename__ = "BOX"

    uuid: Mapped[str] = mapped_column(String, primary_key=True)
    created: Mapped[str] = mapped_column(String)
    picture_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="pending")
    licenceplate: Mapped[str | None] = mapped_column(String, nullable=True)
    licenceplate_status: Mapped[str | None] = mapped_column(String, nullable=True)
    licenceplate_desc: Mapped[str | None] = mapped_column(String, nullable=True)
    vin: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_status: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_car: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_production_year: Mapped[str | None] = mapped_column(String, nullable=True)


class BoxDetail(Base):
    __tablename__ = "BOX_DETAIL"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String)
    picture: Mapped[str] = mapped_column(String)
    attr_name: Mapped[str] = mapped_column(String)
    attr_value: Mapped[str] = mapped_column(String)
