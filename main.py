import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers import auth, classify, documents

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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


@app.get("/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0",
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
