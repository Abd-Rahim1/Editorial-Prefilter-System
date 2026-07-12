"""
UJA Editorial Processing Pipeline — API Gateway
Registers all routers, runs startup DB migrations, and configures CORS.
"""
import sys
import os
import traceback
import logging
from fastapi import FastAPI, Request

logger = logging.getLogger("APIGateway")
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Ensure apps/api and packages directories are in sys.path when starting uvicorn from root
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_current_dir, '..', '..'))
_packages_dir = os.path.join(_project_root, 'packages')

if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)
if _packages_dir not in sys.path:
    sys.path.insert(0, _packages_dir)

from config import engine, Base, SessionLocal, SystemSettings, RoleModel
from routers import pipelines
from routers.auth import router as auth_router
from routers.admin import router as admin_router
from routers.admin_portal import router as admin_portal_router
from routers.dashboard import router as dashboard_router
from routers.research import router as research_router
from routers.analytics import router as analytics_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="UJA Editorial Processing Pipeline",
    description="AI-assisted editorial decision support system API.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    traceback.print_exc()
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

app.include_router(auth_router)
app.include_router(pipelines)
app.include_router(admin_router)
app.include_router(admin_portal_router)
app.include_router(dashboard_router)
app.include_router(research_router)
app.include_router(analytics_router)

@app.on_event("startup")
def startup_tasks():
    """
    1. Seed required reference data (roles, default settings).
    2. Run idempotent ALTER TABLE migrations to add columns that were added
       after the initial DB creation (model_runs JSONB payload columns).
    """
    # Seed reference data
    db = SessionLocal()
    try:
        for role_name in ("admin", "editor"):
            if not db.query(RoleModel).filter(RoleModel.name == role_name).first():
                db.add(RoleModel(name=role_name))
        if not db.query(SystemSettings).first():
            db.add(SystemSettings(auto_reject_threshold=0.80, manual_review_threshold=0.50))
        db.commit()
    except Exception as e:
        logger.error(f"Seed error: {e}")
        db.rollback()
    finally:
        db.close()

    # Schema migrations — ADD COLUMN IF NOT EXISTS is fully idempotent
    migration_statements = [
        # model_runs payload columns (missing from initial pgAdmin export)
        "ALTER TABLE public.model_runs ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(100);",
        "ALTER TABLE public.model_runs ADD COLUMN IF NOT EXISTS prompt_text TEXT;",
        "ALTER TABLE public.model_runs ADD COLUMN IF NOT EXISTS input_payload JSONB;",
        "ALTER TABLE public.model_runs ADD COLUMN IF NOT EXISTS raw_output TEXT;",
        "ALTER TABLE public.model_runs ADD COLUMN IF NOT EXISTS parsed_output JSONB;",
        # audit_logs created_at alias guard
        "ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
        # reports.report_json column — persistence.py inserts via raw SQL; ORM model only has report_path
        "ALTER TABLE public.reports ADD COLUMN IF NOT EXISTS report_json JSONB;",
        # Ensure audit_logs.manuscript_id is nullable so activity logging never blocks on edge cases
        "ALTER TABLE public.audit_logs ALTER COLUMN manuscript_id DROP NOT NULL;",
    ]
    with engine.begin() as conn:
        for stmt in migration_statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                logger.warning(f"Migration skipped '{stmt[:60]}...' ({type(e).__name__})")

    logger.info("Database migrations complete. API is ready.")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "UJA Editorial Pipeline"}
