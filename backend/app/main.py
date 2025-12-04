import sys
import os

# --- MAGIC FIX: Add parent directory to path ---
# This allows 'from app import ...' to work without changing all your code
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# -----------------------------------------------

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# These imports will now work because of the fix above
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import accounts, auth, dashboard, notifications, policies

# Note: We don't import seed/crud here to avoid circular dependency issues on startup 
# unless strictly necessary, but the path fix makes them available if needed.

app = FastAPI(title=settings.app_name)

# Allow CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for now to fix 405/CORS issues
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all your routers
for router in (auth.router, accounts.router, policies.router, dashboard.router, notifications.router):
    app.include_router(router)

# Setup API router prefix
api_router = APIRouter(prefix="/api")
for router in (auth.router, accounts.router, policies.router, dashboard.router, notifications.router):
    api_router.include_router(router)
app.include_router(api_router)

@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

@app.on_event("startup")
def on_startup() -> None:
    # This prevents the app from crashing during the build phase if DB isn't ready
    if settings.database_url and not settings.database_url.startswith('sqlite'):
        try:
            # Create tables only if we have a real database connection
            Base.metadata.create_all(bind=engine)
            print("Database tables created.")
        except Exception as e:
            print(f"Warning: Database initialization skipped: {e}")
    else:
        print("Skipping database initialization (SQLite/Build mode)")