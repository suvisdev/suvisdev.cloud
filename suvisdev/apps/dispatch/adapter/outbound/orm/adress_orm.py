from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_neo_theone_base import Base


class DispatchAdressOrm(Base):
    __tablename__ = "dispatch_adress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    middle_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    phonetic_first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    phonetic_middle_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    phonetic_last_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    name_prefix: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    name_suffix: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    nickname: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    file_as: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    organization_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    organization_title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    organization_department: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    birthday: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    photo: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    labels: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    email_label: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
