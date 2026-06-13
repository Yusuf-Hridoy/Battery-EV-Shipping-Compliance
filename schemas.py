from datetime import datetime, date
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


# --- Auth schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    plan: str
    docs_used_this_month: int
    created_at: datetime
    lemonsqueezy_subscription_id: Optional[str] = None
    subscription_status: str = "free"
    current_period_end: Optional[datetime] = None
    perdoc_credits: int = 0
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Classify schemas ---
class ShipmentInput(BaseModel):
    battery_chemistry: Literal["li-ion", "lifepo4", "li-metal", "sodium-ion"]
    packaging_config: Literal["alone", "in_equipment", "with_equipment"]
    transport_mode: Literal["air", "sea", "road"]
    product_type: Optional[str] = None
    watt_hour_rating: Optional[float] = None
    lithium_content_grams: Optional[float] = None
    quantity: int = Field(..., ge=1, le=99999)

    @field_validator("watt_hour_rating")
    @classmethod
    def validate_watt_hours(cls, v):
        if v is not None and (v <= 0 or v >= 100000):
            raise ValueError("Watt-hour rating must be between 0 and 100,000")
        return v

    @field_validator("lithium_content_grams")
    @classmethod
    def validate_lithium_content(cls, v):
        if v is not None and (v <= 0 or v >= 10000):
            raise ValueError("Lithium content must be between 0 and 10,000 grams")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v < 1 or v > 99999:
            raise ValueError("Quantity must be between 1 and 99,999")
        return v


class ClassificationResult(BaseModel):
    un_number: str
    packing_instruction: str
    section: str
    transport_mode: str
    requires_shippers_declaration: bool
    requires_un38_3: bool
    hazard_class: str
    proper_shipping_name: str
    additional_requirements: list[str]
    confidence: str


class ShipmentOut(BaseModel):
    id: UUID
    battery_chemistry: str
    packaging_config: str
    transport_mode: str
    product_type: Optional[str]
    un_number: Optional[str]
    packing_instruction: Optional[str]
    section: Optional[str]
    requires_shippers_declaration: bool
    pdf_generated: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Billing schemas ---
class BillingStatus(BaseModel):
    plan: str
    subscription_status: str
    docs_used_this_month: int
    docs_limit: int
    perdoc_credits: int
    current_period_end: Optional[datetime] = None
    can_generate: bool


# --- Regulation schemas ---
class RegulationUpdateOut(BaseModel):
    id: UUID
    title: str
    body: str
    source: str
    effective_date: date
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
