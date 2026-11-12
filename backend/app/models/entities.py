from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    platform: Mapped[str] = mapped_column(String(40), default="javascript")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    organization: Mapped[Organization] = relationship(back_populates="projects")
    keys: Mapped[list["ProjectKey"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    issues: Mapped[list["Issue"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectKey(Base):
    __tablename__ = "project_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(24))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    project: Mapped[Project] = relationship(back_populates="keys")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("project_id", "fingerprint", name="uq_issue_project_fingerprint"),
        Index("ix_issues_project_status_last_seen", "project_id", "status", "last_seen"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500))
    exception_type: Mapped[str] = mapped_column(String(160), default="Error")
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="error")
    status: Mapped[str] = mapped_column(String(20), default="unresolved", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    affected_users: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    assigned_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project: Mapped[Project] = relationship(back_populates="issues")
    events: Mapped[list["Event"]] = relationship(back_populates="issue", cascade="all, delete-orphan")
    activities: Mapped[list["IssueActivity"]] = relationship(back_populates="issue", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_project_created", "project_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text)
    exception_type: Mapped[str] = mapped_column(String(160), default="Error")
    stacktrace: Mapped[str] = mapped_column(Text, default="")
    environment: Mapped[str] = mapped_column(String(80), default="production")
    user_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    breadcrumbs: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    issue: Mapped[Issue] = relationship(back_populates="events")


class IssueActivity(Base):
    __tablename__ = "issue_activity"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    issue: Mapped[Issue] = relationship(back_populates="activities")
