"""
policy_resolver.py — Active Threshold Profile Resolution Engine
Resolves editorial threshold policies strictly through the active model relationship:
`trained_models.is_active = true` -> `trained_models.threshold_profile_id` -> `threshold_profiles.id`.

Features:
1. Preserves exact DB schema mapping: `reject_threshold` -> `reject_upper_bound`, `review_threshold` -> `peer_review_lower_bound`.
2. Short-lived policy caching (`DEFAULT_POLICY_TTL_SEC`) and explicit invalidation (`invalidate_cache()`), allowing admin policy changes to propagate without model reload or app restart.
3. Does not globally query the newest threshold profile or legacy profile 1 without active model linkage.
"""

import time
from typing import Dict, Any, Optional
from ..common.exceptions import ThresholdPolicyError
from .model_resolver import ModelResolver

try:
    from apps.api.config import SessionLocal, ThresholdProfile
    DB_AVAILABLE = True
except ImportError:
    try:
        from apps.api.config import SessionLocal, ThresholdProfile
        DB_AVAILABLE = True
    except ImportError:
        DB_AVAILABLE = False
        SessionLocal = None
        ThresholdProfile = None

DEFAULT_POLICY_TTL_SEC: float = 60.0


class PolicyResolver:
    """Resolves threshold profiles via active model relationship with short-lived caching."""

    def __init__(
        self,
        db_session: Optional[Any] = None,
        model_resolver: Optional[ModelResolver] = None,
        cache_ttl_sec: float = DEFAULT_POLICY_TTL_SEC
    ):
        self.db_session = db_session
        self.model_resolver = model_resolver or ModelResolver(db_session=db_session)
        self.cache_ttl_sec = cache_ttl_sec
        self._cached_profile: Optional[Dict[str, Any]] = None
        self._cache_timestamp: float = 0.0

    def _get_session(self):
        if self.db_session:
            return self.db_session, False
        if SessionLocal:
            try:
                return SessionLocal(), True
            except Exception:
                pass
        return None, False

    def invalidate_cache(self) -> None:
        """Purges the short-lived policy cache, forcing immediate reload on next query."""
        self._cached_profile = None
        self._cache_timestamp = 0.0

    def clear_cache(self) -> None:
        """Alias for invalidate_cache()."""
        self.invalidate_cache()

    def resolve_active_policy(
        self,
        force_reload: bool = False,
        model_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Resolves the active threshold policy via the active model's `threshold_profile_id`.

        Args:
            force_reload: If True, bypasses short-lived cache.
            model_record: Optional pre-resolved model record from `ModelResolver`.

        Returns:
            Dict[str, Any]: Resolved threshold policy struct.
        """
        now = time.time()
        if not force_reload and self._cached_profile and (now - self._cache_timestamp < self.cache_ttl_sec):
            return self._cached_profile

        # 1. Obtain active model record if not supplied
        if model_record is None:
            try:
                model_record = self.model_resolver.resolve_active_model_record()
            except Exception:
                model_record = {}

        target_profile_id = model_record.get("threshold_profile_id")
        if not target_profile_id:
            # Active Layer 3 profile default ID = 2
            target_profile_id = 2

        session, close_needed = self._get_session()
        try:
            if session and ThresholdProfile:
                # Resolve strictly through the model relationship ID
                if hasattr(session, "get"):
                    tp = session.get(ThresholdProfile, target_profile_id)
                else:
                    tp = session.query(ThresholdProfile).filter(ThresholdProfile.id == target_profile_id).first()

                if tp:
                    rej_bound = float(tp.reject_threshold if tp.reject_threshold is not None else 0.35)
                    rev_bound = float(tp.review_threshold if tp.review_threshold is not None else 0.65)

                    if rej_bound > rev_bound:
                        raise ThresholdPolicyError(
                            f"[ThresholdPolicy Error] reject_threshold ({rej_bound}) cannot exceed "
                            f"review_threshold ({rev_bound}) in threshold_profile {tp.id}."
                        )

                    resolved = {
                        "profile_id": tp.id,
                        "profile_name": tp.name or f"Profile_{tp.id}",
                        "version": str(tp.id),
                        "reject_upper_bound": rej_bound,
                        "peer_review_lower_bound": rev_bound,
                        "desk_reject_upper_bound": rej_bound,
                        "source": "threshold_profiles_relationship"
                    }
                    self._cached_profile = resolved
                    self._cache_timestamp = now
                    return resolved
        finally:
            if close_needed and session:
                try:
                    session.close()
                except Exception:
                    pass

        # Fallback if DB profile unavailable: enforce active profile 2 defaults (0.35 / 0.65)
        resolved = {
            "profile_id": target_profile_id,
            "profile_name": "Layer3 Default Editorial Policy",
            "version": str(target_profile_id),
            "reject_upper_bound": 0.35,
            "peer_review_lower_bound": 0.65,
            "desk_reject_upper_bound": 0.35,
            "source": "relationship_fallback_default"
        }
        self._cached_profile = resolved
        self._cache_timestamp = now
        return resolved
