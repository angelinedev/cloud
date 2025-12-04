import sys
import os

# --- MAGIC FIX: Add parent directory to path ---
# This ensures Vercel can find your app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# -----------------------------------------------

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Imports
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import accounts, auth, dashboard, notifications, policies
from app import crud, schemas  # We need these to create the user
from app.security import PasswordManager # To hash the password manually if needed

app = FastAPI(title=settings.app_name)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
for router in (auth.router, accounts.router, policies.router, dashboard.router, notifications.router):
    app.include_router(router)

# API Router
api_router = APIRouter(prefix="/api")
for router in (auth.router, accounts.router, policies.router, dashboard.router, notifications.router):
    api_router.include_router(router)
app.include_router(api_router)

@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

def create_admin_user(db: Session):
    """Helper to ensure admin exists."""
    try:
        admin_email = "admin@cloudguard.dev"
        # Check if user exists (Assuming a get_user_by_email function exists in crud)
        # If crud is complex, we can do a direct query to be safe:
        from app.models import User
        user = db.query(User).filter(User.email == admin_email).first()
        
        if not user:
            print(f"Creating admin user: {admin_email}")
            # Create the user. We try to use the schema if possible, or fallback to model
            try:
                user_in = schemas.UserCreate(
                    email=admin_email, 
                    password="changeme123", 
                    full_name="Admin User"
                )
                # FIX: Pass the password hasher function as required by crud.create_user
                crud.create_user(db, user_in, PasswordManager.hash)
            except AttributeError:
                # Fallback if schemas/crud names differ
                hashed_pw = PasswordManager.hash("changeme123")
                new_user = User(email=admin_email, hashed_password=hashed_pw, full_name="Admin User", is_active=True)
                db.add(new_user)
                db.commit()
            print("Admin user created successfully.")
        else:
            print("Admin user already exists.")
    except Exception as e:
        print(f"Error creating admin user: {e}")

@app.on_event("startup")
def on_startup() -> None:
    if settings.database_url and not settings.database_url.startswith('sqlite'):
        try:
            # 1. Create Tables
            Base.metadata.create_all(bind=engine)
            print("Database tables created.")

            # 2. Seed Admin User
            db = SessionLocal()
            try:
                create_admin_user(db)
            finally:
                db.close()

        except Exception as e:
            print(f"Warning: Database initialization error: {e}")
    else:
        print("Skipping database initialization (Build mode)")