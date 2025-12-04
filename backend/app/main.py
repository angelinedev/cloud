import sys
import os

# --- MAGIC FIX: Add parent directory to path ---
# This ensures Vercel can find your app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# -----------------------------------------------

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Imports
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import accounts, auth, dashboard, notifications, policies
from app import crud, schemas
from app.security import PasswordManager

# ============ DEMO SEED IMPORT - REMOVE THIS LINE FOR PRODUCTION ============
from app.seed import demo_records
# ============================================================================

app = FastAPI(title=settings.app_name)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DEBUGGING: Log Validation Errors to Vercel Console ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    print(f"❌ VALIDATION ERROR on {request.url}: {error_details}")
    return JSONResponse(
        status_code=422,
        content={"detail": error_details},
    )
# ----------------------------------------------------------

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
        from app.models import User
        user = db.query(User).filter(User.email == admin_email).first()
        
        if not user:
            print(f"Creating admin user: {admin_email}")
            
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

            try:
                user_in = schemas.UserCreate(
                    email=admin_email, 
                    password="changeme123", 
                    full_name="Cloud Guard Admin"
                )
                crud.create_user(db, user_in, pwd_context.hash)
            except AttributeError:
                hashed_pw = pwd_context.hash("changeme123")
                new_user = User(email=admin_email, hashed_password=hashed_pw, full_name="Cloud Guard Admin", is_active=True)
                db.add(new_user)
                db.commit()
            print("✅ Admin user created successfully.")
        else:
            print("ℹ️  Admin user already exists.")
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")

# ============ DEMO SEED FUNCTION - REMOVE THIS FUNCTION FOR PRODUCTION ============
def seed_demo_data(db: Session):
    """Seed demo data from seed.py"""
    try:
        from app.models import User, CloudAccount, Policy, PolicyEvaluation, Notification
        
        # Check if demo data already exists
        account_count = db.query(CloudAccount).count()
        policy_count = db.query(Policy).count()
        eval_count = db.query(PolicyEvaluation).count()
        notif_count = db.query(Notification).count()
        
        if account_count > 0 and policy_count > 0 and eval_count > 0 and notif_count > 0:
            print("ℹ️  Demo data already seeded.")
            return
        
        print("🌱 Seeding demo data...")
        
        # If there's partial data, clean it up first
        if account_count > 0 or policy_count > 0 or eval_count > 0 or notif_count > 0:
            print("⚠️  Partial data detected. Cleaning up...")
            db.query(PolicyEvaluation).delete()
            db.query(Notification).delete()
            db.query(Policy).delete()
            db.query(CloudAccount).delete()
            db.commit()
            print("✅ Cleanup complete")
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        records = demo_records(password_hasher=pwd_context.hash)
        
        # Group records by model type to maintain order
        users = []
        accounts = []
        policies = []
        evaluations = []
        notifications = []
        
        for record in records:
            model = record["model"]
            data = record["data"]
            
            # Skip user creation if it's the admin user (already created by create_admin_user)
            if model == User and data.get("email") == "admin@cloudguard.dev":
                print("ℹ️  Skipping admin user (already exists)")
                continue
            
            if model == User:
                users.append(data)
            elif model == CloudAccount:
                accounts.append(data)
            elif model == Policy:
                policies.append(data)
            elif model == PolicyEvaluation:
                evaluations.append(data)
            elif model == Notification:
                notifications.append(data)
        
        # Insert in correct order to satisfy foreign keys
        # 1. Users (already created by create_admin_user, so skip)
        
        # 2. Cloud Accounts
        for data in accounts:
            instance = CloudAccount(**data)
            db.add(instance)
        db.commit()
        db.flush()  # Ensure IDs are assigned
        print("✅ Cloud accounts created")
        
        # 3. Policies
        for data in policies:
            instance = Policy(**data)
            db.add(instance)
        db.commit()
        db.flush()  # Ensure IDs are assigned
        print("✅ Policies created")
        
        # 4. Policy Evaluations (requires accounts and policies to exist)
        for data in evaluations:
            instance = PolicyEvaluation(**data)
            db.add(instance)
        db.commit()
        print("✅ Policy evaluations created")
        
        # 5. Notifications
        for data in notifications:
            instance = Notification(**data)
            db.add(instance)
        db.commit()
        print("✅ Notifications created")
        
        print("✅ Demo data seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding demo data: {e}")
        print(f"💡 Hint: Try dropping and recreating your database tables")
        db.rollback()
# ===================================================================================

@app.on_event("startup")
def on_startup() -> None:
    if settings.database_url and not settings.database_url.startswith('sqlite'):
        try:
            # 1. Create Tables
            Base.metadata.create_all(bind=engine)
            print("📊 Database tables created.")

            # 2. Create Admin User (if not exists)
            db = SessionLocal()
            try:
                create_admin_user(db)
                
                # ============ DEMO SEED - REMOVE THESE 2 LINES FOR PRODUCTION ============
                seed_demo_data(db)
                # ==========================================================================
                
            finally:
                db.close()

        except Exception as e:
            print(f"⚠️  Warning: Database initialization error: {e}")
    else:
        print("⏭️  Skipping database initialization (Build mode)")