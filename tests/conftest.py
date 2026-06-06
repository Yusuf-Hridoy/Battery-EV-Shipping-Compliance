import pytest


@pytest.fixture
def valid_liion_input():
    return {
        "battery_chemistry": "li-ion",
        "packaging_config": "alone",
        "transport_mode": "air",
        "product_type": None,
        "watt_hour_rating": 50.0,
        "lithium_content_grams": None,
        "quantity": 1,
    }
