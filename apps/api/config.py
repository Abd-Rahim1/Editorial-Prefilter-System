import os
import yaml
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

API_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(API_DIR))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

db_cfg = config.get("database", {})
db_user = os.getenv("DATABASE_USER", db_cfg.get("user", "postgres"))
db_password = os.getenv("DATABASE_PASSWORD", db_cfg.get("password", "postgres123"))
db_host = os.getenv("DATABASE_HOST", db_cfg.get("host", "localhost"))
db_port = os.getenv("DATABASE_PORT", db_cfg.get("port", "5432"))
db_name = os.getenv("DATABASE_NAME", db_cfg.get("dbname", "editorial_prefilter"))

DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



class RoleModel(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    users = relationship("UserModel", back_populates="role_rel")


class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(Text, nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    role_rel = relationship("RoleModel", back_populates="users")


class SystemSettings(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    auto_reject_threshold = Column(Float, default=0.80)
    manual_review_threshold = Column(Float, default=0.50)


class AuditLog(Base):
    """
    Matches the live public.audit_logs schema exactly.
    The column is `created_at` (not `timestamp`).
    """
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    manuscript_id = Column(Integer, ForeignKey("manuscripts.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Manuscript(Base):
    __tablename__ = "manuscripts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    title = Column(Text, nullable=True)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")
    num_pages = Column(Integer, nullable=True)
    total_word_count = Column(Integer, nullable=True)
    ground_truth = Column(Boolean, default=False)

    editorial_features = relationship("EditorialFeature", back_populates="manuscript")
    extracted_sections = relationship("ExtractedSection", back_populates="manuscript")
    llm_evaluations = relationship("LLMEvaluation", back_populates="manuscript")
    model_runs = relationship("ModelRun", back_populates="manuscript")
    reports = relationship("Report", back_populates="manuscript")
    rule_checks = relationship("RuleCheck", back_populates="manuscript")
    audit_logs = relationship("AuditLog", backref="manuscript")


class EditorialFeature(Base):
    __tablename__ = "editorial_features"
    id = Column(Integer, primary_key=True, index=True)
    manuscript_id = Column(Integer, ForeignKey("manuscripts.id"), nullable=False)
    feature_name = Column(String(100), nullable=True)
    feature_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    manuscript = relationship("Manuscript", back_populates="editorial_features")


class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(Integer, primary_key=True, index=True)
    experiment_name = Column(String(255), nullable=True)
    model_version = Column(String(100), nullable=True)
    metrics = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    model_runs = relationship("ModelRun", back_populates="experiment")


class Explanation(Base):
    __tablename__ = "explanations"
    id = Column(Integer, primary_key=True, index=True)
    model_run_id = Column(Integer, ForeignKey("model_runs.id"), nullable=False)
    explanation_text = Column(Text, nullable=True)
    detected_issues = Column(JSONB, nullable=True)
    evidence_spans = Column(JSONB, nullable=True)

    model_run = relationship("ModelRun", back_populates="explanations")


class ExtractedSection(Base):
    __tablename__ = "extracted_sections"
    id = Column(Integer, primary_key=True, index=True)
    manuscript_id = Column(Integer, ForeignKey("manuscripts.id"), nullable=False)
    section_name = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)

    manuscript = relationship("Manuscript", back_populates="extracted_sections")


class LLMEvaluation(Base):
    __tablename__ = "llm_evaluations"
    id = Column(Integer, primary_key=True, index=True)
    manuscript_id = Column(Integer, ForeignKey("manuscripts.id"), nullable=False)
    abstract_clarity = Column(Float, nullable=True)
    structural_completeness = Column(Float, nullable=True)
    methodological_strength = Column(Float, nullable=True)
    experimental_strength = Column(Float, nullable=True)
    argumentative_quality = Column(Float, nullable=True)
    scope_alignment = Column(Float, nullable=True)
    overall_quality = Column(Float, nullable=True)
    research_paper_likelihood = Column(Float, nullable=True)
    integrity_risk_score = Column(Float, nullable=True)
    is_probably_research_paper = Column(Boolean, nullable=True)
    detected_issues = Column(JSONB, nullable=True)
    evidence_spans = Column(JSONB, nullable=True)
    final_integrity_decision = Column(String(50), nullable=True)
    recommendation = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    manuscript = relationship("Manuscript", back_populates="llm_evaluations")


class ModelRun(Base):
    __tablename__ = "model_runs"
    id = Column(Integer, primary_key=True, index=True)
    manuscript_id = Column(Integer, ForeignKey("manuscripts.id"), nullable=False)
    model_version = Column(String(100), nullable=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=True)
    threshold_profile_id = Column(Integer, ForeignKey("threshold_profiles.id"), nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    abstract_clarity = Column(Float, nullable=True)
    structural_completeness = Column(Float, nullable=True)
    methodological_strength = Column(Float, nullable=True)
    experimental_strength = Column(Float, nullable=True)
    argumentative_quality = Column(Float, nullable=True)
    scope_alignment = Column(Float, nullable=True)
    overall_quality = Column(Float, nullable=True)
    prompt_version = Column(String(100), nullable=True)
    prompt_text = Column(Text, nullable=True)
    input_payload = Column(JSONB, nullable=True)
    raw_output = Column(Text, nullable=True)
    parsed_output = Column(JSONB, nullable=True)

    manuscript = relationship("Manuscript", back_populates="model_runs")
    experiment = relationship("Experiment", back_populates="model_runs")
    threshold_profile = relationship("ThresholdProfile", back_populates="model_runs")
    predictions = relationship("Prediction", back_populates="model_run")
    explanations = relationship("Explanation", back_populates="model_run")


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    model_run_id = Column(Integer, ForeignKey("model_runs.id"), nullable=False)
    predicted_label = Column(Boolean, nullable=True)
    desk_reject_probability = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)

    model_run = relationship("ModelRun", back_populates="predictions")


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    manuscript_id = Column(Integer, ForeignKey("manuscripts.id"), nullable=False)
    report_path = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    manuscript = relationship("Manuscript", back_populates="reports")


class RuleCheck(Base):
    __tablename__ = "rule_checks"
    id = Column(Integer, primary_key=True, index=True)
    manuscript_id = Column(Integer, ForeignKey("manuscripts.id"), nullable=False)
    rule_name = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=True)
    passed = Column(Boolean, nullable=True)
    description = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    manuscript = relationship("Manuscript", back_populates="rule_checks")


class ThresholdProfile(Base):
    __tablename__ = "threshold_profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    reject_threshold = Column(Float, nullable=True)
    review_threshold = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    min_abstract_words = Column(Integer, default=150)
    max_abstract_words = Column(Integer, default=240)
    min_keywords = Column(Integer, default=3)
    max_keywords = Column(Integer, default=8)
    min_references = Column(Integer, default=15)
    max_references = Column(Integer, default=50)
    min_journal_self_citations = Column(Integer, default=2)
    max_journal_self_citations = Column(Integer, default=4)
    max_citations_from_any_journal = Column(Integer, default=5)
    max_self_citations_by_authors = Column(Integer, default=4)
    min_ratio_recent_citations = Column(Float, default=0.3)
    min_manuscript_words = Column(Integer, default=8000)
    max_manuscript_words = Column(Integer, default=15000)
    required_sections = Column(ARRAY(Text), nullable=False, default=lambda: ["abstract", "introduction", "methodology", "conclusions", "references"])
    max_missing_sections = Column(Integer, default=2)
    min_section_words = Column(Integer, default=100)
    min_pages = Column(Integer, default=4)
    max_pages = Column(Integer, default=20)

    model_runs = relationship("ModelRun", back_populates="threshold_profile")


class ApiMetric(Base):
    __tablename__ = "api_metrics"
    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), nullable=True)
    method = Column(String(10), nullable=True)
    response_time = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DashboardStatistic(Base):
    __tablename__ = "dashboard_statistics"
    id = Column(Integer, primary_key=True, index=True)
    total_manuscripts = Column(Integer, default=0)
    accepted = Column(Integer, default=0)
    rejected = Column(Integer, default=0)
    review = Column(Integer, default=0)
    average_confidence = Column(Float, default=0.75)
    average_processing_time = Column(Float, default=4.2)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ModelRegistry(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(150), nullable=False)
    version = Column(String(50), nullable=True)
    provider = Column(String(100), nullable=True)
    model_type = Column(String(100), nullable=True)
    context_length = Column(Integer, nullable=True)
    parameters = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    latency_ms = Column(Integer, nullable=True)
    gpu_memory = Column(String(50), nullable=True)
    total_predictions = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    health_status = Column(String(30), default="Healthy")


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=True)
    version = Column(String(30), nullable=True)
    system_prompt = Column(Text, nullable=True)
    user_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TrainedModel(Base):
    __tablename__ = "trained_models"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=True)
    llm_model_id = Column(Integer, nullable=True)
    prompt_template_id = Column(Integer, ForeignKey("prompt_templates.id"), nullable=True)
    threshold_profile_id = Column(Integer, ForeignKey("threshold_profiles.id"), nullable=True)
    model_version = Column(String(100), nullable=True)
    training_dataset = Column(String(255), nullable=True)
    mlflow_run_id = Column(String(100), nullable=True)
    artifact_path = Column(Text, nullable=True)
    scaler_path = Column(Text, nullable=True)
    calibrator_path = Column(Text, nullable=True)
    metrics_path = Column(Text, nullable=True)
    feature_schema_path = Column(Text, nullable=True)
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auroc = Column(Float, nullable=True)
    ece = Column(Float, nullable=True)
    training_duration_seconds = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=False)
    trained_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("ModelRegistry", foreign_keys=[model_id])
    experiment = relationship("Experiment", foreign_keys=[experiment_id])
    prompt_template = relationship("PromptTemplate", foreign_keys=[prompt_template_id])
    threshold_profile = relationship("ThresholdProfile", foreign_keys=[threshold_profile_id])



class SystemHealth(Base):
    __tablename__ = "system_health"
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=True)
    status = Column(String(50), nullable=True)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)


class ThresholdHistory(Base):
    __tablename__ = "threshold_history"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("threshold_profiles.id"), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reject_threshold = Column(Float, nullable=True)
    review_threshold = Column(Float, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)


class UserActivity(Base):
    __tablename__ = "user_activity"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    activity = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    theme = Column(String(20), default="dark")
    language = Column(String(20), default="en")
    dashboard_layout = Column(String(100), nullable=True)
    items_per_page = Column(Integer, default=10)



def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()