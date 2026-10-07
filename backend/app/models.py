import enum
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SystemType(str, enum.Enum):
    on_grid = "on_grid"
    off_grid = "off_grid"
    hybrid = "hybrid"


class ProjectSegment(str, enum.Enum):
    commercial = "commercial"
    industrial = "industrial"


class ProductType(str, enum.Enum):
    pv = "pv"
    pv_battery = "pv_battery"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    system_type: Mapped[SystemType] = mapped_column(
        Enum(SystemType), default=SystemType.on_grid, nullable=False
    )
    segment: Mapped[Optional[ProjectSegment]] = mapped_column(Enum(ProjectSegment), nullable=True)
    product_type: Mapped[Optional[ProductType]] = mapped_column(Enum(ProductType), nullable=True)
    pv_capacity_kw: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    battery_capacity_kwh: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    inverter_capacity_kw: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    grid_connected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    compliance_checks: Mapped[List["ComplianceCheck"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )


class Severity(str, enum.Enum):
    critical = "critical"
    low = "low"
    medium = "medium"
    high = "high"



class CheckStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    warning = "warning"
    pending = "pending"


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity), default=Severity.low, nullable=False
    )
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="compliance_checks")
