import logging

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import User

logger = logging.getLogger("batteryship")


async def reset_monthly_docs():
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                update(User).values(docs_used_this_month=0)
            )
            await session.commit()
            logger.info("Monthly document count reset for all users.")
        except Exception as e:
            await session.rollback()
            logger.error(f"Monthly reset failed: {str(e)}")
