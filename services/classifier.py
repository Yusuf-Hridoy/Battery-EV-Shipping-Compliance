"""
BatteryShip Classification Engine

Pure Python logic for classifying lithium batteries for international shipping.
No external APIs, no database calls — fast and deterministic.
"""

VALID_CHEMISTRIES = {"li-ion", "lifepo4", "li-metal", "sodium-ion"}
VALID_PACKAGING = {"alone", "in_equipment", "with_equipment"}
VALID_TRANSPORT = {"air", "sea", "road"}


def classify(
    battery_chemistry: str,
    packaging_config: str,
    transport_mode: str,
    product_type: str | None = None,
    watt_hour_rating: float | None = None,
    lithium_content_grams: float | None = None,
    quantity: int = 1,
) -> dict:
    """
    Classify a battery shipment and return IATA-compliant metadata.
    """
    # ------------------------------------------------------------------
    # RULE 0 — Input validation
    # ------------------------------------------------------------------
    if battery_chemistry not in VALID_CHEMISTRIES:
        raise ValueError(
            f"Invalid battery_chemistry: {battery_chemistry!r}. "
            f"Must be one of {VALID_CHEMISTRIES}."
        )
    if packaging_config not in VALID_PACKAGING:
        raise ValueError(
            f"Invalid packaging_config: {packaging_config!r}. "
            f"Must be one of {VALID_PACKAGING}."
        )
    if transport_mode not in VALID_TRANSPORT:
        raise ValueError(
            f"Invalid transport_mode: {transport_mode!r}. "
            f"Must be one of {VALID_TRANSPORT}."
        )

    # ------------------------------------------------------------------
    # Initialise defaults
    # ------------------------------------------------------------------
    un_number: str | None = None
    packing_instruction: str | None = None
    section = "N/A"
    proper_shipping_name: str | None = None
    requires_shippers_declaration = False
    requires_un38_3 = False
    hazard_class = "Class 9"
    confidence = "high"
    additional_requirements: list[str] = []
    special_rules_triggered = 0

    sodium_override = False
    ebike_override = False
    ev_pack_override = False

    # ------------------------------------------------------------------
    # RULE 1 — Sodium-ion (checked first)
    # ------------------------------------------------------------------
    if battery_chemistry == "sodium-ion":
        sodium_override = True
        un_number = "UN3551"
        packing_instruction = "Refer to IATA DGR Section 3"
        proper_shipping_name = "Sodium-ion batteries"
        requires_un38_3 = True
        confidence = "low"
        additional_requirements.extend([
            "New UN number effective 2025",
            "Verify classification with DG specialist",
            "IATA DGR 2026 Section 3 applies",
        ])
        special_rules_triggered += 1

    # ------------------------------------------------------------------
    # RULE 2 — E-bikes / E-scooters
    # ------------------------------------------------------------------
    elif product_type in ("ebike", "escooter"):
        ebike_override = True
        if battery_chemistry in ("li-ion", "lifepo4"):
            un_number = "UN3556"
            proper_shipping_name = "Vehicle, lithium ion battery powered"
        elif battery_chemistry == "li-metal":
            un_number = "UN3557"
            proper_shipping_name = "Vehicle, lithium metal battery powered"
        packing_instruction = "Refer to IATA DGR Special Provision A154"
        requires_un38_3 = True
        confidence = "medium"
        additional_requirements.extend([
            "Reclassified under new 2025 UN codes (previously UN3171)",
            "Special Provision A154 applies",
            "Verify SoC requirements with carrier",
            "CAO (Cargo Aircraft Only) restrictions may apply",
        ])
        special_rules_triggered += 1

    # ------------------------------------------------------------------
    # RULE 3 — EV battery packs
    # ------------------------------------------------------------------
    elif product_type == "ev_pack":
        ev_pack_override = True
        if battery_chemistry in ("li-ion", "lifepo4"):
            un_number = "UN3480"
        elif battery_chemistry == "li-metal":
            un_number = "UN3090"
        additional_requirements.extend([
            "UN38.3 Test Summary required",
            "Port of Ningbo requires UN38.3 report submission",
            "Carrier pre-approval required for large format cells",
        ])
        confidence = "medium"
        special_rules_triggered += 1

    # ------------------------------------------------------------------
    # RULE 4 & 5 — Standard rechargeable / non-rechargeable
    # ------------------------------------------------------------------
    if not sodium_override and not ebike_override:
        if battery_chemistry in ("li-ion", "lifepo4"):
            if packaging_config == "alone":
                un_number = "UN3480"
                packing_instruction = "PI965"
                proper_shipping_name = "Lithium ion batteries"
            elif packaging_config == "in_equipment":
                un_number = "UN3481"
                packing_instruction = "PI966"
                proper_shipping_name = "Lithium ion batteries contained in equipment"
            elif packaging_config == "with_equipment":
                un_number = "UN3481"
                packing_instruction = "PI967"
                proper_shipping_name = "Lithium ion batteries packed with equipment"
        elif battery_chemistry == "li-metal":
            if packaging_config == "alone":
                un_number = "UN3090"
                packing_instruction = "PI968"
                proper_shipping_name = "Lithium metal batteries"
            elif packaging_config == "in_equipment":
                un_number = "UN3091"
                packing_instruction = "PI969"
                proper_shipping_name = "Lithium metal batteries contained in equipment"
            elif packaging_config == "with_equipment":
                un_number = "UN3091"
                packing_instruction = "PI970"
                proper_shipping_name = "Lithium metal batteries packed with equipment"

        # Re-apply ev_pack UN override after standard rules set PI & name
        if ev_pack_override:
            if battery_chemistry in ("li-ion", "lifepo4"):
                un_number = "UN3480"
            elif battery_chemistry == "li-metal":
                un_number = "UN3090"

    # ------------------------------------------------------------------
    # RULE 6 — Section determination (air only)
    # ------------------------------------------------------------------
    if transport_mode == "air":
        if sodium_override:
            section = "N/A"
        elif battery_chemistry in ("li-ion", "lifepo4"):
            if packaging_config == "alone" and quantity == 1:
                # Cell
                if watt_hour_rating is not None:
                    section = "I" if watt_hour_rating > 20 else "II"
                else:
                    section = "I"
                    additional_requirements.append(
                        "Watt-hour rating not provided — defaulted to Section I (fully regulated). "
                        "Provide Wh rating for accurate classification."
                    )
                    confidence = "medium"
            else:
                # Battery or in/with equipment
                if watt_hour_rating is not None:
                    section = "I" if watt_hour_rating > 100 else "II"
                else:
                    section = "I"
                    additional_requirements.append(
                        "Watt-hour rating not provided — defaulted to Section I (fully regulated). "
                        "Provide Wh rating for accurate classification."
                    )
                    confidence = "medium"
        elif battery_chemistry == "li-metal":
            if packaging_config == "alone" and quantity == 1:
                if lithium_content_grams is not None:
                    section = "I" if lithium_content_grams > 1 else "II"
                else:
                    section = "I"
                    additional_requirements.append(
                        "Watt-hour rating not provided — defaulted to Section I (fully regulated). "
                        "Provide Wh rating for accurate classification."
                    )
                    confidence = "medium"
            else:
                if lithium_content_grams is not None:
                    section = "I" if lithium_content_grams > 2 else "II"
                else:
                    section = "I"
                    additional_requirements.append(
                        "Watt-hour rating not provided — defaulted to Section I (fully regulated). "
                        "Provide Wh rating for accurate classification."
                    )
                    confidence = "medium"
    else:
        section = "N/A"

    # ------------------------------------------------------------------
    # RULE 7 — requires_shippers_declaration
    # ------------------------------------------------------------------
    if product_type == "ev_pack":
        requires_shippers_declaration = True
    elif section == "II" and transport_mode == "air":
        requires_shippers_declaration = False
    elif transport_mode == "road" and packaging_config == "in_equipment":
        requires_shippers_declaration = False
    elif section == "I":
        requires_shippers_declaration = True
    elif transport_mode == "sea" and un_number in ("UN3480", "UN3090"):
        requires_shippers_declaration = True
    else:
        requires_shippers_declaration = False

    # ------------------------------------------------------------------
    # RULE 8 — requires_un38_3
    # ------------------------------------------------------------------
    if product_type in ("ev_pack", "ebike", "escooter"):
        requires_un38_3 = True
    elif section == "II" and packaging_config == "in_equipment" and transport_mode == "air" and quantity <= 2:
        requires_un38_3 = False
    else:
        requires_un38_3 = True

    # ------------------------------------------------------------------
    # RULE 9 — Confidence scoring
    # ------------------------------------------------------------------
    if sodium_override:
        confidence = "low"
    elif special_rules_triggered > 1:
        confidence = "low"
    elif ebike_override or ev_pack_override:
        confidence = "medium"
    elif battery_chemistry in ("li-ion", "lifepo4", "li-metal"):
        rating_provided = (
            (battery_chemistry in ("li-ion", "lifepo4") and watt_hour_rating is not None)
            or (battery_chemistry == "li-metal" and lithium_content_grams is not None)
        )
        if rating_provided:
            confidence = "high"
        else:
            confidence = "medium"

    # ------------------------------------------------------------------
    # RULE 10 — Additional requirements by transport mode
    # ------------------------------------------------------------------
    if transport_mode == "air":
        air_reqs = [
            "Class 9 hazard label required on outer package",
            "Lithium battery mark (UN symbol) required",
        ]
        if section == "I":
            air_reqs.append("Cargo Aircraft Only (CAO) label if Section I")
        additional_requirements.extend(air_reqs)
    elif transport_mode == "sea":
        additional_requirements.extend([
            "IMDG Code compliance required",
            "Emergency Response contact required on documentation",
            "Class 9 placard on pallet if >= 500kg gross",
        ])
    elif transport_mode == "road":
        additional_requirements.extend([
            "ADR compliance required",
            "Class 9 placard on vehicle if load exceeds threshold",
        ])

    # ------------------------------------------------------------------
    # Build result
    # ------------------------------------------------------------------
    return {
        "un_number": un_number or "",
        "packing_instruction": packing_instruction or "",
        "section": section,
        "transport_mode": transport_mode,
        "requires_shippers_declaration": requires_shippers_declaration,
        "requires_un38_3": requires_un38_3,
        "hazard_class": hazard_class,
        "proper_shipping_name": proper_shipping_name or "",
        "additional_requirements": additional_requirements,
        "confidence": confidence,
    }


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def get_un_number_info(un_number: str) -> dict:
    """Return reference information for a given UN number."""
    data = {
        "UN3480": {
            "description": "Lithium ion batteries",
            "hazard_class": "Class 9",
            "applicable_regulations": ["IATA DGR", "IMDG Code", "ADR"],
            "common_products": ["Power banks", "Standalone Li-ion cells", "Drone batteries"],
        },
        "UN3481": {
            "description": "Lithium ion batteries contained in or packed with equipment",
            "hazard_class": "Class 9",
            "applicable_regulations": ["IATA DGR", "IMDG Code", "ADR"],
            "common_products": ["Laptops", "Smartphones", "Tablets", "Cameras"],
        },
        "UN3090": {
            "description": "Lithium metal batteries",
            "hazard_class": "Class 9",
            "applicable_regulations": ["IATA DGR", "IMDG Code", "ADR"],
            "common_products": ["Watch batteries", "CMOS batteries", "Medical implants"],
        },
        "UN3091": {
            "description": "Lithium metal batteries contained in or packed with equipment",
            "hazard_class": "Class 9",
            "applicable_regulations": ["IATA DGR", "IMDG Code", "ADR"],
            "common_products": ["PC motherboards", "IoT sensors", "Tracking devices"],
        },
        "UN3551": {
            "description": "Sodium-ion batteries",
            "hazard_class": "Class 9",
            "applicable_regulations": ["IATA DGR 2026 Section 3"],
            "common_products": ["Grid storage", "Emerging EV prototypes"],
        },
        "UN3556": {
            "description": "Vehicle, lithium ion battery powered",
            "hazard_class": "Class 9",
            "applicable_regulations": ["IATA DGR Special Provision A154"],
            "common_products": ["E-bikes", "E-scooters", "Electric mopeds"],
        },
        "UN3557": {
            "description": "Vehicle, lithium metal battery powered",
            "hazard_class": "Class 9",
            "applicable_regulations": ["IATA DGR Special Provision A154"],
            "common_products": ["Light EVs with primary lithium cells"],
        },
        "UN3558": {
            "description": "Sodium-ion batteries contained in or packed with equipment",
            "hazard_class": "Class 9",
            "applicable_regulations": ["IATA DGR 2026 Section 3"],
            "common_products": ["Emerging sodium-ion powered devices"],
        },
    }
    return data.get(un_number, {
        "description": "Unknown UN number",
        "hazard_class": "N/A",
        "applicable_regulations": [],
        "common_products": [],
    })


def get_supported_chemistries() -> list[dict]:
    """Return supported battery chemistries with display names."""
    return [
        {
            "value": "li-ion",
            "display_name": "Lithium-ion (Li-ion)",
            "description": "Rechargeable lithium-ion cells and batteries",
        },
        {
            "value": "lifepo4",
            "display_name": "Lithium Iron Phosphate (LiFePO4)",
            "description": "Rechargeable LiFePO4 cells and batteries",
        },
        {
            "value": "li-metal",
            "display_name": "Lithium Metal",
            "description": "Non-rechargeable lithium metal cells and batteries",
        },
        {
            "value": "sodium-ion",
            "display_name": "Sodium-ion",
            "description": "Emerging sodium-ion battery technology",
        },
    ]


def get_supported_packaging_configs() -> list[dict]:
    """Return supported packaging configurations."""
    return [
        {
            "value": "alone",
            "display_name": "Batteries Alone",
            "description": "Batteries shipped without equipment",
        },
        {
            "value": "in_equipment",
            "display_name": "Contained in Equipment",
            "description": "Batteries installed inside equipment",
        },
        {
            "value": "with_equipment",
            "display_name": "Packed with Equipment",
            "description": "Batteries packed in same box as equipment",
        },
    ]
