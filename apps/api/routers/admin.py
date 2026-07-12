from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, confloat
from sqlalchemy.orm import Session

from auth import TokenData, require_role
from config import get_db, UserModel, RoleModel, SystemSettings, AuditLog, ThresholdProfile

router = APIRouter(tags=["Administration"])



class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str


class SettingsPatch(BaseModel):
    auto_reject_threshold: confloat(ge=0.0, le=1.0)
    manual_review_threshold: confloat(ge=0.0, le=1.0)


class ThresholdsResponse(BaseModel):
    auto_reject_threshold: float
    manual_review_threshold: float



@router.get("/api/v1/admin/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    """Returns all platform user accounts with their role assignments."""
    users = db.query(UserModel).join(RoleModel, UserModel.role_id == RoleModel.id, isouter=True).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email or "",
            "role": u.role_rel.name if u.role_rel else "unknown",
        }
        for u in users
    ]



@router.patch("/api/v1/admin/settings", response_model=ThresholdsResponse)
def update_settings(
    payload: SettingsPatch,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    """Updates the auto-reject and manual-review threshold boundaries."""
    settings = db.query(SystemSettings).first()
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Global system settings are not configured.",
        )
    settings.auto_reject_threshold = payload.auto_reject_threshold
    settings.manual_review_threshold = payload.manual_review_threshold
    db.add(settings)

    tp = db.query(ThresholdProfile).order_by(ThresholdProfile.id.asc()).first()
    if not tp:
        tp = ThresholdProfile(name="default", reject_threshold=payload.auto_reject_threshold, review_threshold=payload.manual_review_threshold, is_active=True)
        db.add(tp)
    else:
        tp.reject_threshold = payload.auto_reject_threshold
        tp.review_threshold = payload.manual_review_threshold

    audit = AuditLog(
        action="UPDATE_SETTINGS",
        details=(
            f"Admin '{current_user.username}' updated thresholds: "
            f"reject={payload.auto_reject_threshold}, review={payload.manual_review_threshold}"
        ),
    )
    db.add(audit)
    db.commit()

    return {
        "auto_reject_threshold": settings.auto_reject_threshold,
        "manual_review_threshold": settings.manual_review_threshold,
    }



@router.get("/api/thresholds", response_model=ThresholdsResponse)
def get_thresholds(db: Session = Depends(get_db)):
    """Returns the current decision thresholds. No auth required for display."""
    from packages.database.config_repository import ConfigRepository
    tp = ConfigRepository(db).get_threshold_profile()
    return {
        "auto_reject_threshold": tp.get("reject_threshold", 0.80),
        "manual_review_threshold": tp.get("review_threshold", 0.50),
    }


@router.put("/api/thresholds", response_model=ThresholdsResponse)
def put_thresholds(
    payload: SettingsPatch,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    """PUT alias kept for backward compatibility with the frontend thresholds page."""
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db.add(settings)

    settings.auto_reject_threshold = payload.auto_reject_threshold
    settings.manual_review_threshold = payload.manual_review_threshold

    tp = db.query(ThresholdProfile).order_by(ThresholdProfile.id.asc()).first()
    if not tp:
        tp = ThresholdProfile(name="default", reject_threshold=payload.auto_reject_threshold, review_threshold=payload.manual_review_threshold, is_active=True)
        db.add(tp)
    else:
        tp.reject_threshold = payload.auto_reject_threshold
        tp.review_threshold = payload.manual_review_threshold

    audit = AuditLog(
        action="UPDATE_THRESHOLDS",
        details=(
            f"Admin '{current_user.username}' updated thresholds via PUT: "
            f"reject={payload.auto_reject_threshold}, review={payload.manual_review_threshold}"
        ),
    )
    db.add(audit)
    db.commit()

    return {
        "auto_reject_threshold": settings.auto_reject_threshold,
        "manual_review_threshold": settings.manual_review_threshold,
    }
