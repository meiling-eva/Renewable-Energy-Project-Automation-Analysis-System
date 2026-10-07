from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models import CheckStatus, ProductType, ProjectSegment, Severity, SystemType

Capacity = Optional[Decimal]


class ProjectBase(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    system_type: SystemType = SystemType.on_grid
    segment: Optional[ProjectSegment] = None
    product_type: Optional[ProductType] = None
    pv_capacity_kw: Capacity = Field(None, ge=0, max_digits=10, decimal_places=2)
    battery_capacity_kwh: Capacity = Field(None, ge=0, max_digits=10, decimal_places=2)
    inverter_capacity_kw: Capacity = Field(None, ge=0, max_digits=10, decimal_places=2)
    grid_connected: bool = True


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    project_name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    system_type: Optional[SystemType] = None
    segment: Optional[ProjectSegment] = None
    product_type: Optional[ProductType] = None
    pv_capacity_kw: Capacity = Field(None, ge=0, max_digits=10, decimal_places=2)
    battery_capacity_kwh: Capacity = Field(None, ge=0, max_digits=10, decimal_places=2)
    inverter_capacity_kw: Capacity = Field(None, ge=0, max_digits=10, decimal_places=2)
    grid_connected: Optional[bool] = None


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("pv_capacity_kw", "battery_capacity_kwh", "inverter_capacity_kw")
    def _capacity_as_number(self, value: Optional[Decimal]) -> Optional[float]:
        return None if value is None else float(value)


class ComplianceCheckCreate(BaseModel):
    rule_code: str = Field(..., min_length=1, max_length=50)
    rule_name: str = Field(..., min_length=1, max_length=255)
    severity: Severity = Severity.low
    status: CheckStatus
    message: Optional[str] = None


class ComplianceCheckRead(ComplianceCheckCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime
