from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AdressRowSchema(BaseModel):
    """Google Contacts CSV 한 행 — alias는 실제 CSV 헤더."""

    model_config = ConfigDict(populate_by_name=True)

    first_name: str = Field(default="", alias="First Name")
    middle_name: str = Field(default="", alias="Middle Name")
    last_name: str = Field(default="", alias="Last Name")
    phonetic_first_name: str = Field(default="", alias="Phonetic First Name")
    phonetic_middle_name: str = Field(default="", alias="Phonetic Middle Name")
    phonetic_last_name: str = Field(default="", alias="Phonetic Last Name")
    name_prefix: str = Field(default="", alias="Name Prefix")
    name_suffix: str = Field(default="", alias="Name Suffix")
    nickname: str = Field(default="", alias="Nickname")
    file_as: str = Field(default="", alias="File As")
    organization_name: str = Field(default="", alias="Organization Name")
    organization_title: str = Field(default="", alias="Organization Title")
    organization_department: str = Field(default="", alias="Organization Department")
    birthday: str = Field(default="", alias="Birthday")
    notes: str = Field(default="", alias="Notes")
    photo: str = Field(default="", alias="Photo")
    labels: str = Field(default="", alias="Labels")
    email_label: str = Field(default="", alias="E-mail 1 - Label")
    email: str = Field(default="", alias="E-mail 1 - Value")


class AdressIntroduceSchema(BaseModel):
    id: int
    name: str


class AdressSearchItemSchema(BaseModel):
    name: str
    email: str
