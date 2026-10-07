import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from lib import store
from routers import analysis, history, rules_catalog, settings as settings_routes


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


# Startup runs before the yield, shutdown after it.
@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(store.init_db)  # SQLite (history + settings); no external services
    yield


# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# --- connectivity probe (template pattern) ----------------------------------

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatusCheckCreate(BaseModel):
    client_name: str


@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    return StatusCheck(**status_dict)


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    return []


# --- SENTINEL routers ---------------------------------------------------------

api_router.include_router(analysis.router)
api_router.include_router(rules_catalog.router)
api_router.include_router(history.router)
api_router.include_router(settings_routes.router)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
