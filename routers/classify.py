import uuid

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Shipment
from schemas import ShipmentInput, ShipmentOut
from services.classifier import classify
from services.auth import check_plan_limit
from services.gemini import explain_classification, check_edge_case
from routers.auth import get_current_user

router = APIRouter()


@router.post("/")
async def classify_shipment(
    input: ShipmentInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = check_plan_limit(current_user.plan, current_user.docs_used_this_month)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Monthly document limit reached for {current_user.plan} plan. Please upgrade to continue.",
        )

    try:
        result = classify(
            battery_chemistry=input.battery_chemistry,
            packaging_config=input.packaging_config,
            transport_mode=input.transport_mode,
            product_type=input.product_type,
            watt_hour_rating=input.watt_hour_rating,
            lithium_content_grams=input.lithium_content_grams,
            quantity=input.quantity,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    shipment = Shipment(
        id=uuid.uuid4(),
        user_id=current_user.id,
        battery_chemistry=input.battery_chemistry,
        packaging_config=input.packaging_config,
        transport_mode=input.transport_mode,
        product_type=input.product_type,
        watt_hour_rating=input.watt_hour_rating,
        lithium_content_grams=input.lithium_content_grams,
        quantity=input.quantity,
        un_number=result["un_number"],
        packing_instruction=result["packing_instruction"],
        section=result["section"],
        requires_shippers_declaration=result["requires_shippers_declaration"],
        requires_un38_3=result["requires_un38_3"],
        hazard_class=result["hazard_class"],
        proper_shipping_name=result["proper_shipping_name"],
        confidence=result["confidence"],
    )
    db.add(shipment)

    current_user.docs_used_this_month += 1
    db.add(current_user)

    await db.flush()
    await db.refresh(shipment)

    response = dict(result)
    response["shipment_id"] = str(shipment.id)
    return response


@router.get("/history", response_model=list[ShipmentOut])
async def history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Shipment)
        .where(Shipment.user_id == current_user.id)
        .order_by(desc(Shipment.created_at))
        .limit(20)
    )
    shipments = result.scalars().all()
    return shipments


@router.get("/options")
async def options():
    return {
        "battery_chemistries": [
            {"value": "li-ion", "label": "Lithium-ion (Li-ion)",
             "description": "Rechargeable. Common in phones, laptops, power banks."},
            {"value": "lifepo4", "label": "Lithium Iron Phosphate (LiFePO4)",
             "description": "Rechargeable. Common in e-bikes, solar storage."},
            {"value": "li-metal", "label": "Lithium Metal",
             "description": "Non-rechargeable. Common in watches, medical devices."},
            {"value": "sodium-ion", "label": "Sodium-ion (Na-ion)",
             "description": "Rechargeable. Emerging technology, new 2025 UN codes apply."},
        ],
        "packaging_configs": [
            {"value": "alone", "label": "Battery alone",
             "description": "Battery shipped by itself, not inside or with any device."},
            {"value": "in_equipment", "label": "Battery in equipment",
             "description": "Battery is installed inside a device (e.g. laptop with battery inside)."},
            {"value": "with_equipment", "label": "Battery with equipment",
             "description": "Battery packed separately alongside the device in same box."},
        ],
        "transport_modes": [
            {"value": "air", "label": "Air freight",
             "description": "IATA DGR applies. Strictest rules."},
            {"value": "sea", "label": "Sea freight",
             "description": "IMDG Code applies."},
            {"value": "road", "label": "Road freight",
             "description": "ADR applies."},
        ],
        "product_types": [
            {"value": "power_bank", "label": "Power bank"},
            {"value": "ebike", "label": "E-bike"},
            {"value": "escooter", "label": "E-scooter"},
            {"value": "ev_pack", "label": "EV battery pack"},
            {"value": "consumer_electronics", "label": "Consumer electronics"},
            {"value": "other", "label": "Other"},
        ],
    }


class ExplainRequest(BaseModel):
    shipment_id: str
    user_question: Optional[str] = None


@router.post("/explain")
async def explain(
    body: ExplainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        shipment_uuid = uuid.UUID(body.shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment ID format")

    result = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_uuid,
            Shipment.user_id == current_user.id,
        )
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    classification = {
        "un_number": shipment.un_number,
        "proper_shipping_name": shipment.proper_shipping_name,
        "packing_instruction": shipment.packing_instruction,
        "section": shipment.section,
        "transport_mode": shipment.transport_mode,
        "requires_shippers_declaration": shipment.requires_shippers_declaration,
        "requires_un38_3": shipment.requires_un38_3,
        "hazard_class": shipment.hazard_class,
        "confidence": shipment.confidence,
        "additional_requirements": [],
    }

    user_id = str(current_user.id)
    if body.user_question:
        return check_edge_case(body.user_question, classification, user_id)
    return explain_classification(classification, user_id)
