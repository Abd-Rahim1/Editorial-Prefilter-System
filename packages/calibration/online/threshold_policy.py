"""
threshold_policy.py — Configurable Editorial Threshold Policy Engine
Applies pure probability-to-decision mapping (`evaluate_decision`) converting acceptance probabilities
into standardized recommendations (`desk_reject`, `manual_review`, `peer_review`).
Delegates active profile resolution and short-lived caching to `PolicyResolver`.
"""

from typing import Dict, Any, Tuple, Optional
from ..common.exceptions import ThresholdPolicyError
from .policy_resolver import PolicyResolver


class ThresholdPolicy:
    """Configurable threshold policy engine managing decision boundaries and confidence categories."""

    def __init__(self, db_session: Optional[Any] = None, policy_resolver: Optional[PolicyResolver] = None):
        self.db_session = db_session
        self.resolver = policy_resolver or PolicyResolver(db_session=db_session)

    def get_active_profile(
        self,
        custom_profile: Optional[Dict[str, Any]] = None,
        force_reload: bool = False,
        model_record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fetches the active threshold profile via `PolicyResolver` unless overridden by `custom_profile`."""
        if custom_profile:
            return custom_profile
        return self.resolver.resolve_active_policy(force_reload=force_reload, model_record=model_record)

    def evaluate_decision(
        self,
        p_accept: float,
        profile: Optional[Dict[str, Any]] = None,
        force_reload: bool = False,
        model_record: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, str, Dict[str, float]]:
        """Maps an acceptance probability `p_accept` into an editorial recommendation and confidence category.

        Args:
            p_accept: Bounded probability P(Accept) [0.0, 1.0].
            profile: Optional active profile dict overriding boundaries.
            force_reload: If True, invalidates cache and re-fetches policy.
            model_record: Optional pre-resolved model record from `ModelResolver`.

        Returns:
            Tuple[str, str, str, Dict[str, float]]:
                - decision: 'desk_reject' | 'manual_review' | 'peer_review'
                - confidence_level: 'HIGH' | 'MODERATE'
                - profile_version: Version identifier string
                - thresholds_used: Dictionary of boundary cutoffs applied
        """
        prof = self.get_active_profile(custom_profile=profile, force_reload=force_reload, model_record=model_record)
        
        # Support both DB runtime terms (`reject_upper_bound`) and legacy/compatibility terms (`desk_reject_upper_bound`)
        desk_bound = float(
            prof.get("reject_upper_bound", prof.get("desk_reject_upper_bound", prof.get("reject_threshold", 0.35)))
        )
        review_bound = float(
            prof.get("peer_review_lower_bound", prof.get("review_threshold", 0.65))
        )
        version_str = str(prof.get("version", prof.get("profile_version", "v1.0")))

        if desk_bound > review_bound:
            raise ThresholdPolicyError(
                f"[ThresholdPolicy Error] reject_upper_bound ({desk_bound}) cannot exceed "
                f"peer_review_lower_bound ({review_bound})."
            )

        thresholds_used = {
            "desk_reject_upper_bound": desk_bound,
            "peer_review_lower_bound": review_bound,
            "reject_upper_bound": desk_bound
        }

        # 1. Desk Reject
        if p_accept <= desk_bound:
            confidence = "HIGH" if p_accept <= (desk_bound * 0.6) else "MODERATE"
            return "desk_reject", confidence, version_str, thresholds_used

        # 2. Peer Review
        if p_accept >= review_bound:
            confidence = "HIGH" if p_accept >= min(1.0, review_bound + 0.15) else "MODERATE"
            return "peer_review", confidence, version_str, thresholds_used

        # 3. Manual Editorial Review
        return "manual_review", "MODERATE", version_str, thresholds_used
