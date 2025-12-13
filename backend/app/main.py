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
import logging

# Imports
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import accounts, auth, dashboard, notifications, policies
from app import crud, schemas
from app.security import PasswordManager

# ============ DEMO SEED IMPORT - REMOVE THIS LINE FOR PRODUCTION ============
from app.seed import demo_records
# ============================================================================

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ============================================================================
# CORS CONFIGURATION - CRITICAL FOR VERCEL DEPLOYMENT
# ============================================================================
# Allow all origins in development, specific origins in production
is_development = getattr(settings, 'environment', 'production') == "development"

# IMPORTANT: For Vercel, we need to be permissive during development/testing
# Update the allowed origins list once you have your production frontend URL
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://cloudguard-gamma.vercel.app",
    "https://*.vercel.app",  # Allow all Vercel preview deployments
]

# In development, allow everything for easier testing
if is_development:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
    ],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Additional CORS handling for OPTIONS requests
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """Handle OPTIONS requests (CORS preflight)"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        },
    )

# ============================================================================

# --- DEBUGGING: Log Validation Errors to Vercel Console ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    logger.error(f"❌ VALIDATION ERROR on {request.url}: {error_details}")
    return JSONResponse(
        status_code=422,
        content={"detail": error_details},
    )
# ----------------------------------------------------------

# API Router - Single registration point
api_router = APIRouter(prefix="/api")
for router in (auth.router, accounts.router, policies.router, dashboard.router, notifications.router):
    api_router.include_router(router)
app.include_router(api_router)

@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Health check endpoint for monitoring"""
    return {"status": "ok", "version": "1.0.0"}

def create_admin_user(db: Session) -> None:
    """
    Helper to ensure admin user exists.
    Optimized to reduce database queries.
    """
    try:
        admin_email = "admin@cloudguard.dev"
        from app.models import User
        
        # Check if admin exists
        user = db.query(User).filter(User.email == admin_email).first()
        
        if user:
            logger.info(f"ℹ️  Admin user already exists: {admin_email}")
            return
        
        logger.info(f"Creating admin user: {admin_email}")
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        try:
            user_in = schemas.UserCreate(
                email=admin_email,
                password="changeme123",
                full_name="Cloud Guard Admin"
            )
            crud.create_user(db, user_in, pwd_context.hash)
            logger.info("✅ Admin user created successfully.")
        except AttributeError:
            # Fallback if schemas don't work
            hashed_pw = pwd_context.hash("changeme123")
            new_user = User(
                email=admin_email,
                hashed_password=hashed_pw,
                full_name="Cloud Guard Admin",
                is_active=True
            )
            db.add(new_user)
            db.commit()
            logger.info("✅ Admin user created successfully (fallback method).")
            
    except Exception as e:
        logger.error(f"❌ Error creating admin user: {e}")
        db.rollback()

# ============ DEMO SEED FUNCTION - REMOVE THIS FUNCTION FOR PRODUCTION ============
def seed_demo_data(db: Session) -> None:
    """
    Seed demo data from seed.py
    Optimized with better error handling and progress tracking
    """
    try:
        from app.models import User, CloudAccount, Policy, PolicyEvaluation, Notification
        
        # Check if demo data already exists
        account_count = db.query(CloudAccount).count()
        if account_count >= 3:
            logger.info("ℹ️  Demo data already seeded.")
            return
        
        logger.info("🌱 Seeding demo data...")
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        records = demo_records(password_hasher=pwd_context.hash)
        
        # Organize records by type
        records_by_type = {
            User: [],
            CloudAccount: [],
            Policy: [],
            PolicyEvaluation: [],
            Notification: []
        }
        
        for record in records:
            model = record["model"]
            data = record["data"]
            
            # Skip user - admin already exists
            if model == User:
                continue
            
            if model in records_by_type:
                records_by_type[model].append(data)
        
        # Create accounts
        logger.info(f"📦 Creating {len(records_by_type[CloudAccount])} cloud accounts...")
        created_accounts = []
        for data in records_by_type[CloudAccount]:
            instance = CloudAccount(**data)
            db.add(instance)
            db.flush()
            created_accounts.append(instance)
        db.commit()
        logger.info(f"✅ Created {len(created_accounts)} cloud accounts")
        
        # Create policies
        logger.info(f"📋 Creating {len(records_by_type[Policy])} policies...")
        created_policies = []
        for data in records_by_type[Policy]:
            instance = Policy(**data)
            db.add(instance)
            db.flush()
            created_policies.append(instance)
        db.commit()
        logger.info(f"✅ Created {len(created_policies)} policies")
        
        # Create ID mappings
        policy_id_map = {i+1: policy.id for i, policy in enumerate(created_policies)}
        account_id_map = {i+1: account.id for i, account in enumerate(created_accounts)}
        
        # Create evaluations
        logger.info(f"🔍 Creating {len(records_by_type[PolicyEvaluation])} policy evaluations...")
        for data in records_by_type[PolicyEvaluation]:
            eval_data = data.copy()
            eval_data['policy_id'] = policy_id_map.get(data['policy_id'], data['policy_id'])
            eval_data['account_id'] = account_id_map.get(data['account_id'], data['account_id'])
            instance = PolicyEvaluation(**eval_data)
            db.add(instance)
        db.commit()
        logger.info(f"✅ Created {len(records_by_type[PolicyEvaluation])} policy evaluations")
        
        # Create notifications
        logger.info(f"🔔 Creating {len(records_by_type[Notification])} notifications...")
        for data in records_by_type[Notification]:
            instance = Notification(**data)
            db.add(instance)
        db.commit()
        logger.info(f"✅ Created {len(records_by_type[Notification])} notifications")
        
        logger.info("✅ Demo data seeded successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error seeding demo data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise  # Re-raise to prevent silent failures
# ===================================================================================

@app.on_event("startup")
def on_startup() -> None:
    """
    Application startup handler
    Optimized to prevent multiple database connections
    """
    # Skip initialization for SQLite (local dev/build mode)
    if not settings.database_url or settings.database_url.startswith('sqlite'):
        logger.info("⏭️  Skipping database initialization (Build/Local mode)")
        return
    
    try:
        logger.info("🚀 Initializing database...")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("📊 Database tables created/verified.")
        
        # Single database session for all initialization
        db = SessionLocal()
        try:
            # Create admin user
            create_admin_user(db)
            
            # ============ DEMO SEED - REMOVE THESE 2 LINES FOR PRODUCTION ============
            seed_demo_data(db)
            # ==========================================================================
            
            logger.info("✅ Database initialization complete!")
            
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"⚠️  Database initialization failed: {e}")
        # Don't crash the app - it might still work for read operations
        import traceback
        traceback.print_exc()

@app.get("/debug/counts")
def debug_counts():
    """
    Debug endpoint to check database counts
    Optimized with single database query pattern
    """
    db = SessionLocal()
    try:
        from app.models import User, CloudAccount, Policy, PolicyEvaluation, Notification
        
        # Fetch all data in single session
        users = db.query(User).all()
        accounts = db.query(CloudAccount).all()
        policies = db.query(Policy).all()
        evaluations_count = db.query(PolicyEvaluation).count()
        notifications_count = db.query(Notification).count()
        
        return {
            "status": "ok",
            "database_url": settings.database_url[:20] + "..." if settings.database_url else "None",
            "users_count": len(users),
            "users": [{"id": u.id, "email": u.email, "full_name": u.full_name} for u in users],
            "accounts_count": len(accounts),
            "accounts": [{"id": a.id, "provider": a.provider, "display_name": a.display_name} for a in accounts],
            "policies_count": len(policies),
            "policies": [
                {
                    "id": p.id,
                    "name": p.name,
                    "provider": p.provider,
                    "has_policy_content": bool(p.policy_content) if hasattr(p, 'policy_content') else False
                }
                for p in policies
            ],
            "evaluations_count": evaluations_count,
            "notifications_count": notifications_count,
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()

@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "message": "CloudGuard API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }