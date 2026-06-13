import logging
import os
import hmac
import hashlib
import httpx
from typing import Optional

LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY")
LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID")
LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

VARIANT_IDS = {
    "starter": os.getenv("LEMONSQUEEZY_VARIANT_STARTER", "1759368"),
    "growth": os.getenv("LEMONSQUEEZY_VARIANT_GROWTH", "1786187"),
    "perdoc": os.getenv("LEMONSQUEEZY_VARIANT_PERDOC", "1786194"),
}

PLAN_NAMES = {
    "1759368": "starter",
    "1786187": "growth",
    "1786194": "perdoc",
}

LS_API_BASE = "https://api.lemonsqueezy.com/v1"
LS_HEADERS = {
    "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
}


logger = logging.getLogger("batteryship")


def create_checkout_url(variant_id: str, user_email: str, user_id: str) -> str:
    """Create a Lemon Squeezy checkout URL for the given variant."""
    if not LEMONSQUEEZY_API_KEY:
        raise ValueError("LEMONSQUEEZY_API_KEY is not set")
    if not LEMONSQUEEZY_STORE_ID:
        raise ValueError("LEMONSQUEEZY_STORE_ID is not set")
    if not variant_id:
        raise ValueError("variant_id is required")

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user_email,
                    "custom": {
                        "user_id": user_id
                    }
                },
                "product_options": {
                    "redirect_url": f"{APP_URL}/app.html?upgraded=true",
                    "receipt_link_url": f"{APP_URL}/app.html?upgraded=true",
                }
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": LEMONSQUEEZY_STORE_ID
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": variant_id
                    }
                }
            }
        }
    }

    try:
        with httpx.Client() as client:
            response = client.post(
                f"{LS_API_BASE}/checkouts",
                headers=LS_HEADERS,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            checkout_url = data["data"]["attributes"]["url"]
            return checkout_url
    except Exception as e:
        logger.error(f"Failed to create Lemon Squeezy checkout: {str(e)}")
        raise ValueError(f"Failed to create checkout: {str(e)}")


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify that the webhook came from Lemon Squeezy."""
    try:
        expected = hmac.new(
            LEMONSQUEEZY_WEBHOOK_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def get_plan_from_variant(variant_id: str) -> str:
    """Return plan name from variant ID."""
    return PLAN_NAMES.get(variant_id, "free")


def cancel_subscription(subscription_id: str) -> bool:
    """Cancel a Lemon Squeezy subscription."""
    try:
        with httpx.Client() as client:
            response = client.delete(
                f"{LS_API_BASE}/subscriptions/{subscription_id}",
                headers=LS_HEADERS,
                timeout=30.0,
            )
            return response.status_code in (200, 204)
    except Exception:
        return False
