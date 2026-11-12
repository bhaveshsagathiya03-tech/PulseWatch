from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)
    organization_name: str = Field(default="My workspace", min_length=2, max_length=160)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1] or len(value) > 255:
            raise ValueError("A valid email address is required")
        return value


class LoginIn(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1] or len(value) > 255:
            raise ValueError("A valid email address is required")
        return value


class ProjectCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    platform: str = Field(default="javascript", max_length=40)
    organization_id: str | None = None


class IssueActionIn(BaseModel):
    action: str
    value: str | None = None


class IngestEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    event_id: str | None = None
    message: str = Field(default="Unhandled error", max_length=8000)
    exception_type: str = Field(default="Error", max_length=160)
    stacktrace: str = Field(default="", max_length=50000)
    severity: str = Field(default="error", max_length=20)
    environment: str = Field(default="production", max_length=80)
    user_id: str | None = Field(default=None, max_length=160)
    url: str | None = Field(default=None, max_length=2048)
    timestamp: datetime | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, Any] = Field(default_factory=dict)
    breadcrumbs: list[dict[str, Any]] = Field(default_factory=list)


class ProjectOut(BaseModel):
    id: str
    name: str
    platform: str
    organization_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
