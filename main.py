import os
import logging
import traceback
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import init_db
from routers import auth, classify, documents, billing
from services.reset import reset_monthly_docs

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("batteryship")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Schedule monthly reset on 1st of every month at 00:05 UTC
    scheduler.add_job(
        reset_monthly_docs,
        CronTrigger(day=1, hour=0, minute=5),
        id="monthly_reset",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — monthly reset scheduled.")

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped.")


app = FastAPI(
    title="BatteryShip API",
    version="1.0.0",
    description="Lithium battery shipping compliance and document generation",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(classify.router, prefix="/api/classify", tags=["classify"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {request.method} {request.url}: "
        f"{str(exc)}\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again.",
            "path": str(request.url.path),
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    # Only return JSON for API routes, not static file 404s
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=404,
            content={"detail": f"Endpoint {request.url.path} not found"}
        )
    # For non-API 404s return a clean 404 response
    return Response(status_code=404)


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0",
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
