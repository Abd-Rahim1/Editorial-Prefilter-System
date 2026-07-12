"""
Admin Portal Router — Exposes all AI Governance and System Management endpoints.
Follows clean architecture: React -> API Client -> FastAPI Router -> Service -> Repository -> PostgreSQL.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session

from config import get_db
from services.admin_service import AdminService
from auth import TokenData, get_current_user

router = APIRouter(tags=["AI Governance & Admin Portal"])

def get_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(db)

@router.get("/admin/dashboard")
@router.get("/api/v1/admin/dashboard")
def get_dashboard(service: AdminService = Depends(get_service)):
    return service.get_dashboard_data()

@router.get("/admin/statistics")
@router.get("/api/v1/admin/statistics")
def get_statistics(service: AdminService = Depends(get_service)):
    data = service.get_dashboard_data()
    return data["kpis"]

@router.get("/admin/thresholds")
@router.get("/api/v1/admin/thresholds")
def get_thresholds(service: AdminService = Depends(get_service)):
    return service.get_thresholds()

@router.put("/admin/thresholds")
@router.patch("/api/v1/admin/settings")
def update_thresholds(
    payload: Dict[str, Any] = Body(...),
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    reject = payload.get("auto_reject_threshold", payload.get("reject_threshold", 0.80))
    review = payload.get("manual_review_threshold", payload.get("review_threshold", 0.50))
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    return service.update_thresholds(float(reject), float(review), user_id)

@router.get("/admin/rules")
@router.get("/api/v1/admin/rules")
def get_rules(service: AdminService = Depends(get_service)):
    return service.get_editorial_rules()

@router.put("/admin/rules")
@router.put("/api/v1/admin/rules")
@router.patch("/api/v1/admin/rules")
def update_rules(
    payload: Dict[str, Any] = Body(...),
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    return service.update_editorial_rules(payload, user_id)

@router.get("/admin/prompts")
@router.get("/api/v1/admin/prompts")
def get_prompts(service: AdminService = Depends(get_service)):
    return service.get_prompts()

@router.post("/admin/prompts")
@router.post("/api/v1/admin/prompts")
def create_prompt(
    payload: Dict[str, Any] = Body(...),
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    return service.create_prompt(payload, user_id)

@router.put("/admin/prompts/{prompt_id}")
@router.put("/api/v1/admin/prompts/{prompt_id}")
def update_prompt(
    prompt_id: int,
    payload: Dict[str, Any] = Body(...),
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    res = service.update_prompt(prompt_id, payload, user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    return res

@router.post("/admin/prompts/{prompt_id}/activate")
@router.post("/api/v1/admin/prompts/{prompt_id}/activate")
def activate_prompt(
    prompt_id: int,
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    res = service.update_prompt(prompt_id, {"is_active": True}, user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    return res

@router.delete("/admin/prompts/{prompt_id}")
@router.delete("/api/v1/admin/prompts/{prompt_id}")
def delete_prompt(
    prompt_id: int,
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    if not service.delete_prompt(prompt_id, user_id):
        raise HTTPException(status_code=404, detail="Prompt template not found.")
    return {"status": "success", "detail": f"Prompt #{prompt_id} deleted."}

@router.get("/admin/models")
@router.get("/api/v1/admin/models")
def get_models(service: AdminService = Depends(get_service)):
    return service.get_models()

@router.put("/admin/models/{model_id}")
@router.put("/api/v1/admin/models/{model_id}")
def update_model(
    model_id: int,
    payload: Dict[str, Any] = Body(...),
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    res = service.update_model(model_id, payload, user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Model not found.")
    return res

@router.post("/admin/models/{model_id}/activate")
@router.post("/api/v1/admin/models/{model_id}/activate")
def activate_model(
    model_id: int,
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    res = service.activate_model(model_id, user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Model not found.")
    return res

@router.delete("/admin/models/{model_id}")
@router.delete("/api/v1/admin/models/{model_id}")
def delete_model(
    model_id: int,
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    user_id = current_user.id if current_user and hasattr(current_user, "id") else None
    if not service.delete_model(model_id, user_id):
        raise HTTPException(status_code=404, detail="Model not found.")
    return {"status": "success", "detail": f"Model #{model_id} deleted."}

@router.get("/admin/experiments")
@router.get("/api/v1/admin/experiments")
def get_experiments(service: AdminService = Depends(get_service)):
    return service.get_experiments()

@router.get("/admin/users")
@router.get("/api/v1/admin/users")
def get_users(service: AdminService = Depends(get_service)):
    return service.get_users()

@router.post("/admin/users")
@router.post("/api/v1/admin/users")
def create_user(
    payload: Dict[str, Any] = Body(...),
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    admin_id = current_user.id if current_user and hasattr(current_user, "id") else None
    return service.create_user(payload, admin_id)

@router.put("/admin/users/{user_id}")
@router.put("/api/v1/admin/users/{user_id}")
def update_user(
    user_id: int,
    payload: Dict[str, Any] = Body(...),
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    admin_id = current_user.id if current_user and hasattr(current_user, "id") else None
    res = service.update_user(user_id, payload, admin_id)
    if not res:
        raise HTTPException(status_code=404, detail="User not found.")
    return res

@router.delete("/admin/users/{user_id}")
@router.delete("/api/v1/admin/users/{user_id}")
def delete_user(
    user_id: int,
    service: AdminService = Depends(get_service),
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    admin_id = current_user.id if current_user and hasattr(current_user, "id") else None
    if not service.delete_user(user_id, admin_id):
        raise HTTPException(status_code=404, detail="User not found.")
    return {"status": "success", "detail": f"User #{user_id} deleted."}

@router.get("/admin/roles")
@router.get("/api/v1/admin/roles")
def get_roles(service: AdminService = Depends(get_service)):
    return service.get_roles()

@router.get("/admin/system-health")
@router.get("/api/v1/admin/system-health")
def get_system_health(service: AdminService = Depends(get_service)):
    return service.get_system_health()

@router.get("/admin/api-metrics")
@router.get("/api/v1/admin/api-metrics")
def get_api_metrics(service: AdminService = Depends(get_service)):
    return service.get_api_analytics()

@router.get("/admin/audit")
@router.get("/api/v1/admin/audit")
def get_audit(limit: int = Query(100, ge=1, le=1000), service: AdminService = Depends(get_service)):
    return service.get_audit_logs(limit)
