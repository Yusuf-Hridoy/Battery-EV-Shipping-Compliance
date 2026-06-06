import io
import os
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Shipment, RegulationUpdate
from schemas import RegulationUpdateOut
from services.auth import check_plan_limit
from routers.auth import get_current_user
from services.pdf_generator import generate_shippers_declaration

router = APIRouter()


@router.post("/generate/{shipment_id}")
async def generate_document(
    shipment_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        shipment_uuid = uuid.UUID(shipment_id)
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

    if shipment.un_number is None:
        raise HTTPException(status_code=400, detail="Shipment has not been classified yet")

    shipment_dict = {
        "id": str(shipment.id),
        "battery_chemistry": shipment.battery_chemistry,
        "packaging_config": shipment.packaging_config,
        "transport_mode": shipment.transport_mode,
        "product_type": shipment.product_type,
        "watt_hour_rating": shipment.watt_hour_rating,
        "lithium_content_grams": shipment.lithium_content_grams,
        "quantity": shipment.quantity,
        "created_at": shipment.created_at.strftime("%Y-%m-%d %H:%M UTC"),
    }
    classification_dict = {
        "un_number": shipment.un_number,
        "packing_instruction": shipment.packing_instruction,
        "section": shipment.section,
        "requires_shippers_declaration": shipment.requires_shippers_declaration,
        "requires_un38_3": shipment.requires_un38_3,
        "hazard_class": shipment.hazard_class,
        "proper_shipping_name": shipment.proper_shipping_name,
    }

    pdf_bytes = generate_shippers_declaration(shipment_dict, classification_dict)

    shipment.pdf_generated = True
    db.add(shipment)
    await db.flush()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=batteryship_{shipment.un_number}_{str(shipment.id)[:8]}.pdf"
            )
        },
    )


@router.get("/regulations", response_model=list[RegulationUpdateOut])
async def regulations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RegulationUpdate).order_by(desc(RegulationUpdate.effective_date)).limit(10)
    )
    updates = result.scalars().all()
    return updates


@router.post("/regulations/seed")
async def seed_regulations(db: AsyncSession = Depends(get_db)):
    if os.getenv("ENVIRONMENT") != "development":
        raise HTTPException(status_code=403, detail="Seed endpoint only available in development")

    seeds = [
        RegulationUpdate(
            id=uuid.uuid4(),
            title="E-bikes and e-scooters reclassified under new UN codes",
            body=(
                "Effective January 2025, lithium-battery-powered vehicles including "
                "e-bikes and e-scooters are no longer classified under UN3171. "
                "New codes UN3556, UN3557, and UN3558 now apply depending on battery "
                "chemistry. Shippers must update documentation immediately."
            ),
            source="IATA DGR 2026 / ADR 2025",
            effective_date=date(2025, 1, 1),
        ),
        RegulationUpdate(
            id=uuid.uuid4(),
            title="Sodium-ion batteries added to UN classification system",
            body=(
                "The UN Committee of Experts added sodium-ion batteries to the "
                "dangerous goods classification system in 2025. UN3551 now covers "
                "sodium-ion batteries with organic electrolyte. Shippers of these "
                "batteries must comply with new documentation and testing requirements."
            ),
            source="UN Model Regulations Rev. 24 (2025)",
            effective_date=date(2025, 3, 1),
        ),
        RegulationUpdate(
            id=uuid.uuid4(),
            title="Port of Ningbo requires UN38.3 test report for all Class 9 shipments",
            body=(
                "The Port of Ningbo has reinstated the requirement for UN38.3 Test "
                "Reports for all lithium battery shipments classified as Class 9 "
                "Dangerous Goods. This applies to all movements including load, "
                "discharge, transshipment, and transit. Non-compliance results in "
                "cargo refusal and penalties."
            ),
            source="ONE Line Advisory — November 2025",
            effective_date=date(2025, 11, 4),
        ),
        RegulationUpdate(
            id=uuid.uuid4(),
            title="IATA DGR 2026 state of charge update for Section II batteries",
            body=(
                "The 2026 edition of IATA Dangerous Goods Regulations introduces "
                "updated state of charge restrictions. Lithium ion batteries packed "
                "with equipment under Section II packing instructions must now not "
                "exceed 30% of rated capacity. Carriers are actively enforcing this "
                "at point of acceptance."
            ),
            source="IATA DGR 66th Edition (2026)",
            effective_date=date(2026, 1, 1),
        ),
    ]

    for record in seeds:
        db.add(record)

    await db.flush()
    return {"seeded": len(seeds), "message": "Regulation updates seeded successfully"}
