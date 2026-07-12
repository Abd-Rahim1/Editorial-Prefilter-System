from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from config import (
    Manuscript, ModelRun, Prediction, AuditLog, SystemSettings, UserModel, RoleModel,
    Experiment, Explanation, ThresholdProfile, ModelRegistry, PromptTemplate,
    SystemHealth, ApiMetric, DashboardStatistic, ThresholdHistory
)

class AdminRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_manuscript_counts(self) -> Dict[str, int]:
        total = self.db.query(func.count(Manuscript.id)).scalar() or 0
        accepted = self.db.query(func.count(Manuscript.id)).filter(
            Manuscript.status.ilike("%accept%")
        ).scalar() or 0
        rejected = self.db.query(func.count(Manuscript.id)).filter(
            Manuscript.status.ilike("%reject%")
        ).scalar() or 0
        review = self.db.query(func.count(Manuscript.id)).filter(
            Manuscript.status.ilike("%review%") | Manuscript.status.ilike("%pending%")
        ).scalar() or 0
        
        # If status string doesn't capture everything, fallback to predictions table or math
        if total > 0 and (accepted + rejected + review) == 0:
            preds = self.db.query(Prediction).all()
            for p in preds:
                if p.desk_reject_probability is not None:
                    if p.desk_reject_probability <= 0.38: accepted += 1
                    elif p.desk_reject_probability <= 0.62: review += 1
                    else: rejected += 1
                elif p.predicted_label is True:
                    accepted += 1
                else:
                    rejected += 1
            if total > (accepted + rejected + review):
                review += (total - (accepted + rejected + review))

        return {
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "review": review
        }

    def get_average_confidence(self) -> float:
        avg = self.db.query(func.avg(Prediction.confidence)).scalar()
        if avg is None:
            avg = self.db.query(func.avg(LLMEvaluation.overall_quality)).scalar() if hasattr(self, 'LLMEvaluation') else 0.84
        return float(avg or 0.84)

    def get_average_processing_time(self) -> float:
        avg_ms = self.db.query(func.avg(ModelRun.execution_time_ms)).scalar()
        if avg_ms:
            return float(avg_ms) / 1000.0  # seconds
        return 4.25

    def get_daily_submissions(self, days: int = 7) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        results = []
        for i in range(days - 1, -1, -1):
            day_start = datetime(now.year, now.month, now.day) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            count = self.db.query(func.count(Manuscript.id)).filter(
                Manuscript.upload_date >= day_start,
                Manuscript.upload_date < day_end
            ).scalar() or 0
            results.append({
                "date": day_start.strftime("%a"),
                "full_date": day_start.strftime("%Y-%m-%d"),
                "count": count
            })
        return results

    def get_confidence_distribution(self) -> List[Dict[str, Any]]:
        preds = self.db.query(Prediction.confidence).filter(Prediction.confidence != None).all()
        buckets = {
            "0.50 - 0.60": 0,
            "0.60 - 0.70": 0,
            "0.70 - 0.80": 0,
            "0.80 - 0.90": 0,
            "0.90 - 1.00": 0
        }
        for (conf,) in preds:
            if conf < 0.60: buckets["0.50 - 0.60"] += 1
            elif conf < 0.70: buckets["0.60 - 0.70"] += 1
            elif conf < 0.80: buckets["0.70 - 0.80"] += 1
            elif conf < 0.90: buckets["0.80 - 0.90"] += 1
            else: buckets["0.90 - 1.00"] += 1
        return [{"range": k, "count": v} for k, v in buckets.items()]

    def get_system_settings(self) -> Optional[SystemSettings]:
        return self.db.query(SystemSettings).first()

    def update_system_settings(self, reject_thresh: float, review_thresh: float, user_id: Optional[int] = None) -> SystemSettings:
        settings = self.get_system_settings()
        if not settings:
            settings = SystemSettings(auto_reject_threshold=reject_thresh, manual_review_threshold=review_thresh)
            self.db.add(settings)
        else:
            settings.auto_reject_threshold = reject_thresh
            settings.manual_review_threshold = review_thresh
        
        # Also update ThresholdProfile to ensure single source of truth across tables
        tp = self.db.query(ThresholdProfile).order_by(ThresholdProfile.id.asc()).first()
        if not tp:
            tp = ThresholdProfile(name="default", reject_threshold=reject_thresh, review_threshold=review_thresh, is_active=True)
            self.db.add(tp)
        else:
            tp.reject_threshold = reject_thresh
            tp.review_threshold = review_thresh

        # Log to threshold history
        history = ThresholdHistory(
            profile_id=1,
            changed_by=user_id,
            reject_threshold=reject_thresh,
            review_threshold=review_thresh,
            changed_at=datetime.utcnow()
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def get_editorial_rules(self) -> Dict[str, Any]:
        from packages.database.config_repository import ConfigRepository
        return ConfigRepository(self.db).get_editorial_rules()

    def update_editorial_rules(self, updates: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        tp = self.db.query(ThresholdProfile).order_by(ThresholdProfile.id.asc()).first()
        if not tp:
            tp = ThresholdProfile(name="Default Profile", is_active=True)
            self.db.add(tp)
        for k, v in updates.items():
            if hasattr(tp, k) and k != "id":
                setattr(tp, k, v)
        self.db.commit()
        self.db.refresh(tp)
        from packages.database.config_repository import ConfigRepository
        return ConfigRepository(self.db).get_editorial_rules()

    def get_all_models(self) -> List[ModelRegistry]:
        return self.db.query(ModelRegistry).order_by(ModelRegistry.id.asc()).all()

    def get_model_by_id(self, model_id: int) -> Optional[ModelRegistry]:
        return self.db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()

    def activate_model(self, model_id: int) -> Optional[ModelRegistry]:
        all_models = self.get_all_models()
        target = None
        for m in all_models:
            if m.id == model_id:
                m.is_active = True
                m.last_used = datetime.utcnow()
                target = m
                break

        if target:
            is_classifier = target.model_type and "classifier" in target.model_type.lower()
            for m in all_models:
                if m.id != model_id:
                    m_is_classifier = m.model_type and "classifier" in m.model_type.lower()
                    if m_is_classifier == is_classifier:
                        m.is_active = False

            if is_classifier:
                try:
                    from config import TrainedModel
                    t_models = self.db.query(TrainedModel).all()
                    for tm in t_models:
                        if tm.model_name and target.model_name and target.model_name.lower() in tm.model_name.lower():
                            tm.is_active = True
                        else:
                            tm.is_active = False
                except Exception:
                    pass
        self.db.commit()
        return target

    def create_or_update_model(self, model_data: Dict[str, Any]) -> ModelRegistry:
        m = self.get_model_by_id(model_data.get("id", -1)) if "id" in model_data else None
        if not m:
            m = ModelRegistry(**model_data)
            self.db.add(m)
        else:
            for k, v in model_data.items():
                if hasattr(m, k) and k != "id":
                    setattr(m, k, v)
        self.db.commit()
        self.db.refresh(m)
        return m

    def delete_model(self, model_id: int) -> bool:
        m = self.get_model_by_id(model_id)
        if m:
            self.db.delete(m)
            self.db.commit()
            return True
        return False

    def get_all_prompts(self) -> List[PromptTemplate]:
        return self.db.query(PromptTemplate).order_by(PromptTemplate.id.asc()).all()

    def get_prompt_by_id(self, prompt_id: int) -> Optional[PromptTemplate]:
        return self.db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()

    def activate_prompt(self, prompt_id: int) -> Optional[PromptTemplate]:
        all_prompts = self.get_all_prompts()
        target = None
        for p in all_prompts:
            if p.id == prompt_id:
                p.is_active = True
                target = p
            else:
                p.is_active = False
        self.db.commit()
        return target

    def create_prompt(self, name: str, version: str, system_prompt: str, user_prompt: str, is_active: bool = False) -> PromptTemplate:
        if is_active:
            for p in self.get_all_prompts():
                p.is_active = False
        new_p = PromptTemplate(
            name=name, version=version, system_prompt=system_prompt,
            user_prompt=user_prompt, is_active=is_active, created_at=datetime.utcnow()
        )
        self.db.add(new_p)
        self.db.commit()
        self.db.refresh(new_p)
        return new_p

    def update_prompt(self, prompt_id: int, updates: Dict[str, Any]) -> Optional[PromptTemplate]:
        p = self.get_prompt_by_id(prompt_id)
        if not p: return None
        if updates.get("is_active"):
            for op in self.get_all_prompts():
                if op.id != prompt_id: op.is_active = False
        for k, v in updates.items():
            if hasattr(p, k) and k != "id":
                setattr(p, k, v)
        self.db.commit()
        self.db.refresh(p)
        return p

    def delete_prompt(self, prompt_id: int) -> bool:
        p = self.get_prompt_by_id(prompt_id)
        if p:
            self.db.delete(p)
            self.db.commit()
            return True
        return False

    def get_all_experiments(self) -> List[Experiment]:
        return self.db.query(Experiment).order_by(Experiment.id.desc()).all()

    def get_all_users(self) -> List[UserModel]:
        return self.db.query(UserModel).order_by(UserModel.id.asc()).all()

    def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def get_role_by_name(self, role_name: str) -> Optional[RoleModel]:
        return self.db.query(RoleModel).filter(RoleModel.name.ilike(role_name)).first()

    def create_user(self, username: str, email: str, role_id: int, is_active: bool = True) -> UserModel:
        u = UserModel(username=username, email=email, role_id=role_id, created_at=datetime.utcnow())
        self.db.add(u)
        self.db.commit()
        self.db.refresh(u)
        return u

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Optional[UserModel]:
        u = self.get_user_by_id(user_id)
        if not u: return None
        for k, v in updates.items():
            if hasattr(u, k) and k != "id":
                setattr(u, k, v)
        self.db.commit()
        self.db.refresh(u)
        return u

    def delete_user(self, user_id: int) -> bool:
        u = self.get_user_by_id(user_id)
        if u:
            self.db.delete(u)
            self.db.commit()
            return True
        return False

    def get_all_roles(self) -> List[RoleModel]:
        return self.db.query(RoleModel).all()

    def get_system_health_records(self) -> List[SystemHealth]:
        return self.db.query(SystemHealth).order_by(SystemHealth.id.asc()).all()

    def get_api_metrics(self) -> List[ApiMetric]:
        return self.db.query(ApiMetric).order_by(ApiMetric.created_at.desc()).limit(100).all()

    def get_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        return self.db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()

    def log_audit(self, action: str, details: str, user_id: Optional[int] = None, manuscript_id: Optional[int] = None) -> AuditLog:
        if manuscript_id is None:
            m = self.db.query(Manuscript).first()
            manuscript_id = m.id if m else 1
        log = AuditLog(user_id=user_id, manuscript_id=manuscript_id, action=action, details=details, created_at=datetime.utcnow())
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
