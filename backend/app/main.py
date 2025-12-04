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
from datetime import datetime, timedelta

# Imports
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import accounts, auth, dashboard, notifications, policies
from app import crud, schemas, models
from app.security import PasswordManager

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

def seed_demo_data(db: Session, password_hasher):
    """Seed demo data from seed.py"""
    try:
        now = datetime.utcnow()
        user_password = password_hasher("changeme123")

        # Check if data already exists
        existing_user = db.query(models.User).filter(models.User.email == "admin@cloudguard.dev").first()
        if existing_user:
            print("Demo data already seeded.")
            return

        print("Seeding demo data...")

        # Create User
        user = models.User(
            email="admin@cloudguard.dev",
            full_name="Cloud Guard Admin",
            hashed_password=user_password,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create Cloud Accounts
        accounts_data = [
            {
                "provider": models.CloudProvider.AWS,
                "external_id": "123456789012",
                "display_name": "AWS Master",
                "status": models.AccountStatus.CONNECTED,
                "created_at": now - timedelta(days=30),
            },
            {
                "provider": models.CloudProvider.AZURE,
                "external_id": "contoso-root",
                "display_name": "Azure Root",
                "status": models.AccountStatus.PENDING,
                "created_at": now - timedelta(days=12),
            },
            {
                "provider": models.CloudProvider.GCP,
                "external_id": "gcp-org",
                "display_name": "GCP Organization",
                "status": models.AccountStatus.ERROR,
                "created_at": now - timedelta(days=7),
            },
        ]

        for account_data in accounts_data:
            account = models.CloudAccount(**account_data)
            db.add(account)
        db.commit()

        # Create Policies
        policies_data = [
            {
                "provider": models.CloudProvider.AWS,
                "name": "Root MFA Enabled",
                "control_id": "AWS-SEC-001",
                "category": "Identity",
                "severity": models.PolicySeverity.CRITICAL,
                "description": "Ensure root account has MFA enabled.",
            },
            {
                "provider": models.CloudProvider.AWS,
                "name": "S3 Public Buckets",
                "control_id": "AWS-STO-010",
                "category": "Storage",
                "severity": models.PolicySeverity.HIGH,
                "description": "Disallow public S3 buckets.",
            },
            {
                "provider": models.CloudProvider.AZURE,
                "name": "Secure Score >= 70",
                "control_id": "AZU-SEC-070",
                "category": "Governance",
                "severity": models.PolicySeverity.MEDIUM,
                "description": "Maintain Azure secure score of at least 70.",
            },
            {
                "provider": models.CloudProvider.GCP,
                "name": "CIS 1.1 Root Accounts",
                "control_id": "GCP-CIS-1.1",
                "category": "Identity",
                "severity": models.PolicySeverity.HIGH,
                "description": "Ensure no active root accounts exist.",
            },
        ]

        for policy_data in policies_data:
            policy = models.Policy(**policy_data)
            db.add(policy)
        db.commit()

        # Create Policy Evaluations
        evaluations_data = [
            {
                "policy_id": 1,
                "account_id": 1,
                "status": models.ComplianceStatus.NON_COMPLIANT,
                "findings": "Root account missing MFA.",
                "last_checked_at": now - timedelta(days=1),
            },
            {
                "policy_id": 2,
                "account_id": 1,
                "status": models.ComplianceStatus.COMPLIANT,
                "findings": "All buckets private.",
                "last_checked_at": now - timedelta(hours=5),
            },
            {
                "policy_id": 3,
                "account_id": 2,
                "status": models.ComplianceStatus.UNKNOWN,
                "findings": "Awaiting latest secure score scan.",
                "last_checked_at": now - timedelta(days=2),
            },
            {
                "policy_id": 4,
                "account_id": 3,
                "status": models.ComplianceStatus.NON_COMPLIANT,
                "findings": "Root project user detected.",
                "last_checked_at": now - timedelta(hours=16),
            },
        ]

        for eval_data in evaluations_data:
            evaluation = models.PolicyEvaluation(**eval_data)
            db.add(evaluation)
        db.commit()

        # Create Notifications
        notifications_data = [
            {
                "title": "Critical policy violation",
                "message": "AWS Root MFA Enabled is failing on account 123456789012.",
                "type": models.NotificationType.POLICY_VIOLATION,
                "created_at": now - timedelta(hours=2, minutes=15),
            },
            {
                "title": "Azure connector pending",
                "message": "Azure Root is waiting for admin consent to finalize the sync.",
                "type": models.NotificationType.ACCOUNT_SYNC,
                "created_at": now - timedelta(hours=1, minutes=5),
            },
            {
                "title": "New compliance report ready",
                "message": "Download the latest tri-cloud readiness assessment from the reports area.",
                "type": models.NotificationType.BUILD_COMPLETE,
                "created_at": now - timedelta(minutes=25),
            },
        ]

        for notif_data in notifications_data:
            notification = models.Notification(**notif_data)
            db.add(notification)
        db.commit()

        print("✅ Demo data seeded successfully!")

    except Exception as e:
        print(f"❌ Error seeding demo data: {e}")
        db.rollback()

@app.on_event("startup")
def on_startup() -> None:
    if settings.database_url and not settings.database_url.startswith('sqlite'):
        try:
            # 1. Create Tables
            Base.metadata.create_all(bind=engine)
            print("Database tables created.")

            # 2. Seed Demo Data
            db = SessionLocal()
            try:
                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                seed_demo_data(db, pwd_context.hash)
            finally:
                db.close()

        except Exception as e:
            print(f"Warning: Database initialization error: {e}")
    else:
        print("Skipping database initialization (Build mode)")