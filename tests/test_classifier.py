import pytest

from services.classifier import classify


# 1.
def test_basic_liion_alone_air():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="alone",
        transport_mode="air",
        watt_hour_rating=50,
    )
    assert result["un_number"] == "UN3480"
    assert result["packing_instruction"] == "PI965"
    assert result["section"] == "I"
    assert result["requires_shippers_declaration"] is True


# 2.
def test_basic_liion_in_equipment_air():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="in_equipment",
        transport_mode="air",
        watt_hour_rating=30,
    )
    assert result["un_number"] == "UN3481"
    assert result["packing_instruction"] == "PI966"
    assert result["section"] == "II"


# 3.
def test_basic_liion_with_equipment_air():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="with_equipment",
        transport_mode="air",
        watt_hour_rating=30,
    )
    assert result["un_number"] == "UN3481"
    assert result["packing_instruction"] == "PI967"
    assert result["section"] == "II"


# 4.
def test_section_ii_small_battery():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="alone",
        transport_mode="air",
        watt_hour_rating=10,
    )
    assert result["un_number"] == "UN3480"
    assert result["packing_instruction"] == "PI965"
    assert result["section"] == "II"
    assert result["requires_shippers_declaration"] is False


# 5.
def test_limetal_alone_air():
    result = classify(
        battery_chemistry="li-metal",
        packaging_config="alone",
        transport_mode="air",
        lithium_content_grams=0.5,
    )
    assert result["un_number"] == "UN3090"
    assert result["packing_instruction"] == "PI968"
    assert result["section"] == "II"


# 6.
def test_limetal_section_i():
    result = classify(
        battery_chemistry="li-metal",
        packaging_config="alone",
        transport_mode="air",
        lithium_content_grams=1.5,
    )
    assert result["un_number"] == "UN3090"
    assert result["packing_instruction"] == "PI968"
    assert result["section"] == "I"
    assert result["requires_shippers_declaration"] is True


# 7.
def test_ebike_liion():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="alone",
        transport_mode="air",
        product_type="ebike",
    )
    assert result["un_number"] == "UN3556"
    assert result["confidence"] == "medium"
    assert any(
        "Reclassified under new 2025 UN codes" in req
        for req in result["additional_requirements"]
    )


# 8.
def test_sodium_ion():
    result = classify(
        battery_chemistry="sodium-ion",
        packaging_config="alone",
        transport_mode="air",
    )
    assert result["un_number"] == "UN3551"
    assert result["confidence"] == "low"
    assert any(
        "New UN number effective 2025" in req
        for req in result["additional_requirements"]
    )


# 9.
def test_sea_transport():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="alone",
        transport_mode="sea",
        watt_hour_rating=100,
    )
    assert result["un_number"] == "UN3480"
    assert result["section"] == "N/A"
    assert result["requires_shippers_declaration"] is True
    assert any(
        "IMDG Code compliance required" in req
        for req in result["additional_requirements"]
    )


# 10.
def test_road_transport():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="in_equipment",
        transport_mode="road",
    )
    assert result["un_number"] == "UN3481"
    assert result["section"] == "N/A"
    assert result["requires_shippers_declaration"] is False


# 11.
def test_no_wh_rating_defaults_to_section_i():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="alone",
        transport_mode="air",
    )
    assert result["section"] == "I"
    assert result["confidence"] == "medium"
    assert any(
        "Watt-hour rating not provided" in req
        for req in result["additional_requirements"]
    )


# 12.
def test_ev_pack_always_requires_un383():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="alone",
        transport_mode="sea",
        product_type="ev_pack",
    )
    assert result["requires_un38_3"] is True
    assert any(
        "UN38.3 Test Summary required" in req
        for req in result["additional_requirements"]
    )


# 13.
def test_invalid_chemistry_raises_error():
    with pytest.raises(ValueError):
        classify(
            battery_chemistry="unknown",
            packaging_config="alone",
            transport_mode="air",
        )


# 14.
def test_invalid_packaging_raises_error():
    with pytest.raises(ValueError):
        classify(
            battery_chemistry="li-ion",
            packaging_config="floating",
            transport_mode="air",
        )


# 15.
def test_high_confidence_complete_input():
    result = classify(
        battery_chemistry="li-ion",
        packaging_config="alone",
        transport_mode="air",
        watt_hour_rating=50,
        product_type="power_bank",
    )
    assert result["confidence"] == "high"
