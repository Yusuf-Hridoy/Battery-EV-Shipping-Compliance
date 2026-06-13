import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import BillingStatus
from services.auth import check_plan_limit, PLAN_LIMITS
from services.billing import (
    create_checkout_url,
    verify_webhook_signature,
    get_plan_from_variant,
    cancel_subscription,
    VARIANT_IDS,
)
from routers.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("batteryship")


def _parse_renews_at(renews_at: Optional[str]) -> Optional[datetime]:
    if not renews_at:
        return None
    try:
        # Lemon Squeezy returns ISO 8601 timestamps
        return datetime.fromisoformat(renews_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


@router.get("/status", response_model=BillingStatus)
async def billing_status(current_user: User = Depends(get_current_user)):
    plan = current_user.plan
    limit = PLAN_LIMITS.get(plan, 3)
    can_generate = check_plan_limit(
        plan,
        current_user.docs_used_this_month,
        current_user.perdoc_credits,
    )["allowed"]

    return BillingStatus(
        plan=plan,
        subscription_status=current_user.subscription_status,
        docs_used_this_month=current_user.docs_used_this_month,
        docs_limit=limit,
        perdoc_credits=current_user.perdoc_credits,
        current_period_end=current_user.current_period_end,
        can_generate=can_generate,
    )


@router.post("/checkout/{plan}")
async def create_checkout(
    plan: str,
    current_user: User = Depends(get_current_user),
):
    if plan not in ["starter", "growth", "perdoc"]:
        raise HTTPException(status_code=400, detail="Invalid plan")

    if current_user.subscription_status == "active" and plan != "perdoc":
        raise HTTPException(
            status_code=400,
            detail="You already have an active subscription. Cancel first to switch plans.",
        )

    variant_id = VARIANT_IDS[plan]

    try:
        url = create_checkout_url(
            variant_id=variant_id,
            user_email=current_user.email,
            user_id=str(current_user.id),
        )
    except ValueError as e:
        logger.error(f"Checkout creation failed for plan={plan}: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail="Could not create checkout session. Please try again.",
        )

    return {"checkout_url": url}


@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = await request.body()
        signature = request.headers.get("X-Signature", "")

        if not verify_webhook_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        event_data = json.loads(payload)
        event_name = request.headers.get("X-Event-Name", "")

        if event_name == "subscription_created":
            attrs = event_data["data"]["attributes"]
            custom_data = attrs.get("custom_data", {})
            user_id = custom_data.get("user_id")
            variant_id = str(attrs.get("variant_id"))
            subscription_id = str(event_data["data"]["id"])
            status = attrs.get("status")
            renews_at = attrs.get("renews_at")
            customer_id = str(attrs.get("customer_id"))

            if user_id:
                result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
                user = result.scalar_one_or_none()
                if user:
                    user.plan = get_plan_from_variant(variant_id)
                    user.subscription_status = "active"
                    user.lemonsqueezy_subscription_id = subscription_id
                    user.lemonsqueezy_customer_id = customer_id
                    user.current_period_end = _parse_renews_at(renews_at)
                    await db.commit()

        elif event_name == "subscription_updated":
            attrs = event_data["data"]["attributes"]
            subscription_id = str(event_data["data"]["id"])
            status = attrs.get("status")
            renews_at = attrs.get("renews_at")
            variant_id = str(attrs.get("variant_id"))

            result = await db.execute(
                select(User).where(User.lemonsqueezy_subscription_id == subscription_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.subscription_status = status
                user.plan = get_plan_from_variant(variant_id)
                user.current_period_end = _parse_renews_at(renews_at)
                if status in ["cancelled", "expired", "past_due"]:
                    user.plan = "free"
                await db.commit()

        elif event_name == "subscription_cancelled":
            subscription_id = str(event_data["data"]["id"])
            result = await db.execute(
                select(User).where(User.lemonsqueezy_subscription_id == subscription_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.subscription_status = "cancelled"
                user.plan = "free"
                await db.commit()

        elif event_name == "order_created":
            attrs = event_data["data"]["attributes"]
            order_status = attrs.get("status")

            if order_status == "paid":
                custom_data = attrs.get("custom_data", {})
                user_id = custom_data.get("user_id")
                first_order_item = attrs.get("first_order_item", {}) or {}
                variant_id = str(first_order_item.get("variant_id", ""))

                if user_id and variant_id == VARIANT_IDS["perdoc"]:
                    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
                    user = result.scalar_one_or_none()
                    if user:
                        user.perdoc_credits += 5
                        await db.commit()

        return JSONResponse({"received": True})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JSONResponse({"received": True})


@router.post("/cancel")
async def cancel_user_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.lemonsqueezy_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription to cancel")

    cancel_subscription(current_user.lemonsqueezy_subscription_id)

    current_user.subscription_status = "cancelled"
    current_user.plan = "free"
    await db.commit()

    return {
        "message": "Subscription cancelled. Access continues until period end."
    }
