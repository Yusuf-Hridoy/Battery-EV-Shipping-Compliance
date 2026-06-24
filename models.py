
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Boolean, Text, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    plan = Column(String(50), default="free")
    docs_used_this_month = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Billing fields (Lemon Squeezy)
    lemonsqueezy_customer_id = Column(String(100), nullable=True)
    lemonsqueezy_subscription_id = Column(String(100), nullable=True)
    subscription_status = Column(String(50), default="free")
    current_period_end = Column(DateTime, nullable=True)
    perdoc_credits = Column(Integer, default=0)

    shipments = relationship("Shipment", back_populates="user")


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    battery_chemistry = Column(String(50), nullable=False)
    packaging_config = Column(String(50), nullable=False)
    transport_mode = Column(String(20), nullable=False)
    product_type = Column(String(50), nullable=True)
    watt_hour_rating = Column(Float, nullable=True)
    lithium_content_grams = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    un_number = Column(String(20), nullable=True)
    packing_instruction = Column(String(100), nullable=True)
    section = Column(String(5), nullable=True)
    requires_shippers_declaration = Column(Boolean, default=False)
    requires_un38_3 = Column(Boolean, default=False)
    hazard_class = Column(String(20), default="Class 9")
    proper_shipping_name = Column(String(255), nullable=True)
    confidence = Column(String(10), nullable=True)
    pdf_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="shipments")


class RegulationUpdate(Base):
    __tablename__ = "regulation_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    effective_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
