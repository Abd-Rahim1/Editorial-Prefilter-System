"""
Centralized Configuration Repository
This repository is the ONLY component that communicates with PostgreSQL for configuration retrieval across Layers 1-4.
Implements connection pooling, unified configuration caching per request, and emergency offline fallback.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_current_dir))
_api_dir = os.path.join(_project_root, "apps", "api")

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

try:
    from config import (
        SessionLocal,
        ModelRegistry,
        PromptTemplate,
        ThresholdProfile,
        SystemSettings,
        TrainedModel,
    )
except ImportError:
    SessionLocal = None
    ModelRegistry = None
    PromptTemplate = None
    ThresholdProfile = None
    SystemSettings = None
    TrainedModel = None


class PipelineConfig:
    """
    Unified configuration object built once when manuscript processing starts
    and reused throughout Layers 1-4 to minimize database access.
    """
    def __init__(
        self,
        active_llm: Dict[str, Any],
        active_prompt: Dict[str, Any],
        active_ml_model: Dict[str, Any],
        editorial_rules: Dict[str, Any],
        threshold_profile: Dict[str, Any],
        system_settings: Dict[str, Any],
    ):
        self.active_llm = active_llm
        self.active_prompt = active_prompt
        self.active_ml_model = active_ml_model
        self.editorial_rules = editorial_rules
        self.threshold_profile = threshold_profile
        self.thresholds = threshold_profile  # Alias for convenience
        self.system_settings = system_settings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_llm": self.active_llm,
            "active_prompt": self.active_prompt,
            "active_ml_model": self.active_ml_model,
            "editorial_rules": self.editorial_rules,
            "threshold_profile": self.threshold_profile,
            "system_settings": self.system_settings,
        }


class ConfigRepository:
    """
    Repository responsible for fetching all dynamic system configuration from PostgreSQL.
    Provides emergency fallback defaults if PostgreSQL is unreachable.
    """
    def __init__(self, db_session=None):
        self._external_session = db_session

    def _get_session(self):
        if self._external_session:
            return self._external_session, False
        if SessionLocal:
            try:
                return SessionLocal(), True
            except Exception as e:
                logging.warning(f"[ConfigRepository] Could not create session from SessionLocal: {e}")
        return None, False

    def get_active_llm(self) -> Dict[str, Any]:
        session, close_needed = self._get_session()
        try:
            if not session or not ModelRegistry:
                return self._get_fallback_llm()

            m = session.query(ModelRegistry).filter(
                ModelRegistry.is_active == True,
                ~ModelRegistry.model_type.ilike("%classifier%")
            ).first()

            if not m:
                # Fallback check for any active LLM
                m = session.query(ModelRegistry).filter(
                    ModelRegistry.model_type.ilike("%llm%")
                ).first()

            if not m:
                return self._get_fallback_llm()

            model_id_str = m.version or m.model_name or "qwen3:4b"
            if ":" in (m.model_name or ""):
                model_id_str = m.model_name
            elif ":" in (m.version or ""):
                model_id_str = m.version

            return {
                "id": m.id,
                "model_name": m.model_name,
                "version": m.version or "qwen3:4b",
                "provider": m.provider or "Ollama GPU Cluster (sinbad2ia)",
                "model_type": m.model_type or "LLM",
                "context_length": m.context_length or 16384,
                "parameters": m.parameters or 4000000000,
                "is_active": m.is_active,
                "latency_ms": m.latency_ms or 15,
                "model_identifier": model_id_str,
            }
        except Exception as e:
            logging.error(f"[ConfigRepository] Error fetching active LLM: {e}. Using fallback.")
            return self._get_fallback_llm()
        finally:
            if close_needed and session:
                try:
                    session.close()
                except Exception:
                    pass

    def _get_fallback_llm(self) -> Dict[str, Any]:
        return {
            "id": 1,
            "model_name": "Qwen",
            "version": "qwen3:4b",
            "provider": "Ollama GPU Cluster (sinbad2ia)",
            "model_type": "LLM",
            "context_length": 16384,
            "parameters": 4000000000,
            "is_active": True,
            "latency_ms": 15,
            "model_identifier": "qwen3:4b",
        }

    def get_active_prompt(self) -> Dict[str, Any]:
        session, close_needed = self._get_session()
        try:
            if not session or not PromptTemplate:
                return self._get_fallback_prompt()

            p = session.query(PromptTemplate).filter(PromptTemplate.is_active == True).first()
            if not p:
                p = session.query(PromptTemplate).first()

            if not p:
                return self._get_fallback_prompt()

            return {
                "id": p.id,
                "name": p.name or "v5_calibrated_json",
                "version": p.version or "v5.0",
                "system_prompt": p.system_prompt or self._get_fallback_prompt()["system_prompt"],
                "user_prompt": p.user_prompt or self._get_fallback_prompt()["user_prompt"],
                "is_active": p.is_active,
                "description": getattr(p, "description", None) or f"Prompt {p.name}",
            }
        except Exception as e:
            logging.error(f"[ConfigRepository] Error fetching active prompt: {e}. Using fallback.")
            return self._get_fallback_prompt()
        finally:
            if close_needed and session:
                try:
                    session.close()
                except Exception:
                    pass

    def _get_fallback_prompt(self) -> Dict[str, Any]:
        return {
            "id": 1,
            "name": "v5_calibrated_json",
            "version": "v5.0",
            "system_prompt": (
                "You are an expert AI academic reviewer. Evaluate the manuscript and output "
                "strict JSON with numerical scores and extracted quote evidence spans."
            ),
            "user_prompt": "Evaluate manuscript text: {text} against Layer 1 rules: {rules}.",
            "is_active": True,
            "description": "Calibrated JSON evaluation prompt",
        }

    def get_active_ml_model(self) -> Dict[str, Any]:
        session, close_needed = self._get_session()
        try:
            if not session:
                return self._get_fallback_ml_model()

            tm = None
            if TrainedModel:
                tm = session.query(TrainedModel).filter(TrainedModel.is_active == True).first()

            if not tm and ModelRegistry:
                # If trained_models table has no active row, check ModelRegistry for active classifier
                m = session.query(ModelRegistry).filter(
                    ModelRegistry.is_active == True,
                    ModelRegistry.model_type.ilike("%classifier%")
                ).first()
                if m:
                    name_lower = (m.model_name or "").lower()
                    if "xgboost" in name_lower or "xgb" in name_lower:
                        path_folder = os.path.join(_project_root, "experiments", "models", "xgboost", "tuned_idx_0", "exp_C", "models")
                    elif "logistic" in name_lower or "logreg" in name_lower or "lr" in name_lower:
                        path_folder = os.path.join(_project_root, "experiments", "models", "logistic_regression", "tuned_idx_0", "exp_C", "models")
                    else:
                        path_folder = os.path.join(_project_root, "experiments", "models", "random_forest", "tuned_idx_0", "exp_C", "models")

                    return {
                        "id": m.id,
                        "model_version": m.version or "v1.0",
                        "experiment_id": 1,
                        "mlflow_run_id": f"run_{m.id}",
                        "artifact_path": os.path.join(path_folder, "model.pkl"),
                        "scaler_path": os.path.join(path_folder, "scaler.pkl"),
                        "metrics_path": os.path.join(path_folder, "metrics.json"),
                        "is_active": True,
                        "model_name": m.model_name,
                    }

            if not tm:
                return self._get_fallback_ml_model()

            art_path = tm.artifact_path or self._get_fallback_ml_model()["artifact_path"]
            if not os.path.isabs(art_path):
                art_path = os.path.join(_project_root, art_path)

            scaler_p = tm.scaler_path or os.path.join(os.path.dirname(art_path), "scaler.pkl")
            if not os.path.isabs(scaler_p):
                scaler_p = os.path.join(_project_root, scaler_p)

            metrics_p = tm.metrics_path or os.path.join(os.path.dirname(art_path), "metrics.json")
            if not os.path.isabs(metrics_p):
                metrics_p = os.path.join(_project_root, metrics_p)

            model_name = "ML Classifier"
            if hasattr(tm, "model") and tm.model and tm.model.model_name:
                model_name = tm.model.model_name

            return {
                "id": tm.id,
                "model_version": tm.model_version or "v1.0",
                "experiment_id": tm.experiment_id or 1,
                "mlflow_run_id": tm.mlflow_run_id or "run_001",
                "artifact_path": art_path,
                "scaler_path": scaler_p,
                "metrics_path": metrics_p,
                "is_active": tm.is_active,
                "model_name": model_name,
            }
        except Exception as e:
            logging.error(f"[ConfigRepository] Error fetching active ML model: {e}. Using fallback.")
            return self._get_fallback_ml_model()
        finally:
            if close_needed and session:
                try:
                    session.close()
                except Exception:
                    pass

    def _get_fallback_ml_model(self) -> Dict[str, Any]:
        default_folder = os.path.join(_project_root, "experiments", "models", "random_forest", "tuned_idx_0", "exp_C", "models")
        return {
            "id": 1,
            "model_version": "random_forest-v1.0",
            "experiment_id": 1,
            "mlflow_run_id": "run_rf_001",
            "artifact_path": os.path.join(default_folder, "model.pkl"),
            "scaler_path": os.path.join(default_folder, "scaler.pkl"),
            "metrics_path": os.path.join(default_folder, "metrics.json"),
            "is_active": True,
            "model_name": "Random Forest",
        }

    def get_editorial_rules(self) -> Dict[str, Any]:
        session, close_needed = self._get_session()
        try:
            if not session or not ThresholdProfile:
                return self._get_fallback_editorial_rules()

            tp = session.query(ThresholdProfile).order_by(ThresholdProfile.id.asc()).first()
            if not tp:
                return self._get_fallback_editorial_rules()

            return {
                "id": tp.id,
                "name": tp.name or "Default Profile",
                "min_abstract_words": tp.min_abstract_words or 150,
                "max_abstract_words": tp.max_abstract_words or 240,
                "min_keywords": tp.min_keywords or 3,
                "max_keywords": tp.max_keywords or 8,
                "min_references": tp.min_references or 15,
                "max_references": tp.max_references or 50,
                "min_journal_self_citations": tp.min_journal_self_citations or 2,
                "max_journal_self_citations": tp.max_journal_self_citations or 4,
                "max_citations_from_any_journal": tp.max_citations_from_any_journal or 5,
                "max_self_citations_by_authors": tp.max_self_citations_by_authors or 4,
                "min_ratio_recent_citations": tp.min_ratio_recent_citations or 0.3,
                "min_manuscript_words": tp.min_manuscript_words or 8000,
                "max_manuscript_words": tp.max_manuscript_words or 15000,
                "required_sections": tp.required_sections or ["abstract", "introduction", "methodology", "conclusions", "references"],
                "max_missing_sections": tp.max_missing_sections or 2,
                "min_section_words": tp.min_section_words or 100,
                "min_pages": tp.min_pages or 4,
                "max_pages": tp.max_pages or 20,
            }
        except Exception as e:
            logging.error(f"[ConfigRepository] Error fetching editorial rules: {e}. Using fallback.")
            return self._get_fallback_editorial_rules()
        finally:
            if close_needed and session:
                try:
                    session.close()
                except Exception:
                    pass

    def _get_fallback_editorial_rules(self) -> Dict[str, Any]:
        return {
            "id": 1,
            "name": "Default Editorial Rules",
            "min_abstract_words": 150,
            "max_abstract_words": 240,
            "min_keywords": 3,
            "max_keywords": 8,
            "min_references": 15,
            "max_references": 50,
            "min_journal_self_citations": 2,
            "max_journal_self_citations": 4,
            "max_citations_from_any_journal": 5,
            "max_self_citations_by_authors": 4,
            "min_ratio_recent_citations": 0.3,
            "min_manuscript_words": 8000,
            "max_manuscript_words": 15000,
            "required_sections": ["abstract", "introduction", "methodology", "conclusions", "references"],
            "max_missing_sections": 2,
            "min_section_words": 100,
            "min_pages": 4,
            "max_pages": 20,
        }

    def get_threshold_profile(self) -> Dict[str, Any]:
        session, close_needed = self._get_session()
        try:
            if not session:
                return self._get_fallback_threshold_profile()

            ss = session.query(SystemSettings).first() if SystemSettings else None
            tp = session.query(ThresholdProfile).order_by(ThresholdProfile.id.asc()).first() if ThresholdProfile else None

            auto_reject = ss.auto_reject_threshold if ss and ss.auto_reject_threshold is not None else (tp.reject_threshold if tp and tp.reject_threshold is not None else 0.80)
            manual_review = ss.manual_review_threshold if ss and ss.manual_review_threshold is not None else (tp.review_threshold if tp and tp.review_threshold is not None else 0.50)

            return {
                "auto_reject_threshold": float(auto_reject),
                "manual_review_threshold": float(manual_review),
                "reject_threshold": float(auto_reject),
                "review_threshold": float(manual_review),
            }
        except Exception as e:
            logging.error(f"[ConfigRepository] Error fetching threshold profile: {e}. Using fallback.")
            return self._get_fallback_threshold_profile()
        finally:
            if close_needed and session:
                try:
                    session.close()
                except Exception:
                    pass

    def get_thresholds(self) -> Dict[str, Any]:
        """Alias for get_threshold_profile() to ensure seamless compatibility."""
        return self.get_threshold_profile()

    def _get_fallback_threshold_profile(self) -> Dict[str, Any]:
        return {
            "auto_reject_threshold": 0.80,
            "manual_review_threshold": 0.50,
            "reject_threshold": 0.80,
            "review_threshold": 0.50,
        }

    def get_system_settings(self) -> Dict[str, Any]:
        session, close_needed = self._get_session()
        try:
            if not session or not SystemSettings:
                return self._get_fallback_system_settings()

            ss = session.query(SystemSettings).first()
            if not ss:
                return self._get_fallback_system_settings()

            return {
                "id": ss.id,
                "auto_reject_threshold": ss.auto_reject_threshold if ss.auto_reject_threshold is not None else 0.80,
                "manual_review_threshold": ss.manual_review_threshold if ss.manual_review_threshold is not None else 0.50,
                "upload_limits_mb": getattr(ss, "upload_limits_mb", 50),
                "execution_timeout_sec": getattr(ss, "execution_timeout_sec", 300),
                "api_configuration": getattr(ss, "api_configuration", {"rate_limit": 100}),
                "queue_size": getattr(ss, "queue_size", 20),
            }
        except Exception as e:
            logging.error(f"[ConfigRepository] Error fetching system settings: {e}. Using fallback.")
            return self._get_fallback_system_settings()
        finally:
            if close_needed and session:
                try:
                    session.close()
                except Exception:
                    pass

    def _get_fallback_system_settings(self) -> Dict[str, Any]:
        return {
            "id": 1,
            "auto_reject_threshold": 0.80,
            "manual_review_threshold": 0.50,
            "upload_limits_mb": 50,
            "execution_timeout_sec": 300,
            "api_configuration": {"rate_limit": 100},
            "queue_size": 20,
        }

    def get_pipeline_config(self) -> PipelineConfig:
        """
        Loads all active configuration once and returns a single PipelineConfig object
        to be passed down and reused across Layers 1-4.
        """
        return PipelineConfig(
            active_llm=self.get_active_llm(),
            active_prompt=self.get_active_prompt(),
            active_ml_model=self.get_active_ml_model(),
            editorial_rules=self.get_editorial_rules(),
            threshold_profile=self.get_threshold_profile(),
            system_settings=self.get_system_settings(),
        )
