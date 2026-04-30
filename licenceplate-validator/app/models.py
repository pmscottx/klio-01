from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class LicencePlate(Base):
    __tablename__ = "LICENCEPLATE"

    licenceplate: Mapped[str] = mapped_column(String, primary_key=True)
    desc: Mapped[str] = mapped_column(String)
