"""SQLAlchemy ORM models.

Mirrors the spec data model (§13). For MVP we keep it flat and SQLite-friendly.
Secrets (IntegrationConfig) are stored encrypted at the application layer before
write — the DB never sees plaintext credentials.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, DateTime, Boolean, Float, Text, JSON, ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(50), default="python")  # python | typescript
    framework: Mapped[str] = mapped_column(String(50), default="fastapi")  # fastapi | express
    environment: Mapped[str] = mapped_column(String(50), default="mock")  # mock | sandbox
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    owner: Mapped["User"] = relationship(back_populates="projects")
    configs: Mapped[list["IntegrationConfig"]] = relationship(back_populates="project")
    test_runs: Mapped[list["TestRun"]] = relationship(back_populates="project")


class IntegrationConfig(Base):
    """Encrypted credential storage. Value is encrypted before persist."""
    __tablename__ = "integration_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    config_type: Mapped[str] = mapped_column(String(50))  # auth | catalog | orders | webhooks
    encrypted_value: Mapped[str] = mapped_column(Text)

    project: Mapped["Project"] = relationship(back_populates="configs")


class TestCase(Base):
    __tablename__ = "test_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))  # auth | catalog | orders | webhooks
    request_definition: Mapped[dict] = mapped_column(JSON)
    expected_definition: Mapped[dict] = mapped_column(JSON)

    test_runs: Mapped[list["TestRun"]] = relationship(back_populates="test_case")


class TestRun(Base):
    __tablename__ = "test_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # passed | failed
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    project: Mapped["Project"] = relationship(back_populates="test_runs")
    test_case: Mapped["TestCase"] = relationship(back_populates="test_runs")
    traces: Mapped[list["RequestTrace"]] = relationship(back_populates="test_run")
    diagnosis: Mapped["Diagnosis | None"] = relationship(back_populates="test_run", uselist=False)


class RequestTrace(Base):
    __tablename__ = "request_traces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"), index=True)
    method: Mapped[str] = mapped_column(String(10))
    url: Mapped[str] = mapped_column(Text)
    request_headers: Mapped[dict] = mapped_column(JSON)
    request_body: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict] = mapped_column(JSON)
    response_body: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ok")

    test_run: Mapped["TestRun"] = relationship(back_populates="traces")


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"), index=True, unique=True)
    problem: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    test_run: Mapped["TestRun"] = relationship(back_populates="diagnosis")
    fixes: Mapped[list["SuggestedFix"]] = relationship(back_populates="diagnosis")


class SuggestedFix(Base):
    __tablename__ = "suggested_fixes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("diagnoses.id"), index=True)
    fix_type: Mapped[str] = mapped_column(String(30))  # code | configuration | documentation
    description: Mapped[str] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_test: Mapped[str] = mapped_column(String(100))

    diagnosis: Mapped["Diagnosis"] = relationship(back_populates="fixes")
    verifications: Mapped[list["VerificationRun"]] = relationship(back_populates="fix")


class VerificationRun(Base):
    __tablename__ = "verification_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fix_id: Mapped[int] = mapped_column(ForeignKey("suggested_fixes.id"), index=True)
    test_run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"))
    status: Mapped[str] = mapped_column(String(20), default="unverified")  # verified | unverified
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    fix: Mapped["SuggestedFix"] = relationship(back_populates="verifications")
