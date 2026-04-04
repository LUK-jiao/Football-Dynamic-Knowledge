"""
Truth Validation Model for event reliability management.

Implements a four-stage validation pipeline before graph persistence:
1) Source-based initial confidence
2) Structural support/conflict relation detection
3) Bidirectional confidence propagation
4) Explainable structured output for persistence layer
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from verifier.event_retrieval import find_related_events_for_validation


class MultiSourceVerifier:
    """Truth Validation Model for football event extraction pipeline."""

    DEFAULT_SOURCE_WEIGHTS: Dict[str, float] = {
        "official": 1.00,
        "official_club": 1.00,
        "fabrizio_romano": 0.90,
        "romano": 0.90,
        "sky_sports": 0.80,
        "media": 0.55,
        "blog": 0.30,
        "unknown": 0.45,
    }

    def __init__(
        self,
        source_weights: Optional[Dict[str, float]] = None,
        alpha: float = 0.30,
        beta: float = 0.40,
        support_threshold: float = 0.45,
        conflict_threshold: float = 0.40,
        candidate_time_window_days: int = 30,
        acceptance_threshold: float = 0.55,
        review_threshold: float = 0.35,
    ):
        self.source_weights = dict(self.DEFAULT_SOURCE_WEIGHTS)
        if source_weights:
            self.source_weights.update(source_weights)

        self.alpha = alpha
        self.beta = beta
        self.support_threshold = support_threshold
        self.conflict_threshold = conflict_threshold
        self.candidate_time_window_days = candidate_time_window_days
        self.acceptance_threshold = acceptance_threshold
        self.review_threshold = review_threshold

    def validate_event(
        self,
        new_event: Dict[str, Any],
        existing_events: Optional[Sequence[Dict[str, Any]]] = None,
        version: int = 1,
        retrieval_limit: int = 100,
        retrieval_time_window_days: int = 30,
    ) -> Dict[str, Any]:
        """Run full four-stage truth validation for one new event."""
        event = deepcopy(new_event)

        # Retrieve candidates from graph when caller doesn't provide existing events.
        if existing_events is None:
            existing_events = find_related_events_for_validation(
                new_event=event,
                limit=retrieval_limit,
                time_window_days=retrieval_time_window_days,
            )

        # Stage 1: Initial confidence by source authority.
        initial_confidence, source_breakdown = self._calculate_initial_confidence(event)
        current_confidence = initial_confidence

        # Stage 2: Candidate selection + relation analysis.
        candidates = self._select_candidates(event, list(existing_events))
        supports: List[Dict[str, Any]] = []
        conflicts: List[Dict[str, Any]] = []
        updated_existing_confidence: Dict[str, float] = {}
        propagation_steps: List[Dict[str, Any]] = []

        for candidate in candidates:
            candidate_id = candidate.get("event_id")
            if not candidate_id:
                continue

            old_confidence = self._safe_confidence(candidate)
            candidate_live_conf = updated_existing_confidence.get(candidate_id, old_confidence)

            slot_aligned = self._same_event_slot(event, candidate)
            if not slot_aligned:
                continue

            support_score = self._support_score(event, candidate)
            conflict_score, conflict_signals = self._conflict_score(event, candidate)

            # Stage 3: Bidirectional propagation.
            propagation_result = self._propagate_confidence(
                current_confidence,
                candidate_live_conf,
                support_score,
                conflict_score,
            )
            current_confidence = propagation_result["new_confidence"]
            updated_existing_confidence[candidate_id] = propagation_result["old_confidence"]

            if support_score >= self.support_threshold:
                supports.append(
                    {
                        "event_id": candidate_id,
                        "score": round(support_score, 4),
                        "participant_overlap": round(self._participant_overlap(event, candidate), 4),
                        "action_similarity": round(self._action_similarity(event, candidate), 4),
                        "time_overlap": round(self._time_overlap(event, candidate), 4),
                    }
                )

            if conflict_score >= self.conflict_threshold:
                conflicts.append(
                    {
                        "event_id": candidate_id,
                        "score": round(conflict_score, 4),
                        "signals": conflict_signals,
                    }
                )

            propagation_steps.append(
                {
                    "event_id": candidate_id,
                    "support_score": round(support_score, 4),
                    "conflict_score": round(conflict_score, 4),
                    "before": {
                        "new_confidence": round(propagation_result["before_new"], 4),
                        "old_confidence": round(propagation_result["before_old"], 4),
                    },
                    "after": {
                        "new_confidence": round(propagation_result["new_confidence"], 4),
                        "old_confidence": round(propagation_result["old_confidence"], 4),
                    },
                }
            )

        current_confidence = self._clamp(current_confidence)
        status = self._resolve_status(current_confidence)

        existing_updates = []
        for candidate in candidates:
            candidate_id = candidate.get("event_id")
            if not candidate_id or candidate_id not in updated_existing_confidence:
                continue
            old_confidence = self._safe_confidence(candidate)
            new_conf = updated_existing_confidence[candidate_id]
            if abs(new_conf - old_confidence) < 1e-9:
                continue
            existing_updates.append(
                {
                    "event_id": candidate_id,
                    "old_confidence": round(old_confidence, 4),
                    "new_confidence": round(new_conf, 4),
                    "delta": round(new_conf - old_confidence, 4),
                }
            )

        validation = {
            "version": version,
            "validated_at": datetime.utcnow().isoformat() + "Z",
            "initial_confidence": round(initial_confidence, 4),
            "current_confidence": round(current_confidence, 4),
            "status": status,
            "source_breakdown": source_breakdown,
            "relation_analysis": {
                "candidate_count": len(candidates),
                "supports": supports,
                "conflicts": conflicts,
            },
            "propagation": {
                "alpha": self.alpha,
                "beta": self.beta,
                "steps": propagation_steps,
                "updated_existing_events": existing_updates,
            },
        }

        event["confidence_score"] = validation["current_confidence"]
        event["validation"] = validation
        return event

    def validate_batch(
        self,
        new_events: Sequence[Dict[str, Any]],
        existing_events: Optional[Sequence[Dict[str, Any]]] = None,
        start_version: int = 1,
        retrieval_limit: int = 100,
        retrieval_time_window_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Validate events sequentially, allowing earlier new events to affect later ones."""
        pool = list(existing_events or [])
        should_auto_retrieve = existing_events is None
        validated: List[Dict[str, Any]] = []

        for idx, event in enumerate(new_events):
            local_existing = list(pool)

            if should_auto_retrieve:
                retrieved = find_related_events_for_validation(
                    new_event=event,
                    limit=retrieval_limit,
                    time_window_days=retrieval_time_window_days,
                )
                known_ids = {e.get("event_id") for e in local_existing if e.get("event_id")}
                for item in retrieved:
                    item_id = item.get("event_id")
                    if item_id and item_id in known_ids:
                        continue
                    local_existing.append(item)
                    if item_id:
                        known_ids.add(item_id)

            validated_event = self.validate_event(
                new_event=event,
                existing_events=local_existing,
                version=start_version + idx,
                retrieval_limit=retrieval_limit,
                retrieval_time_window_days=retrieval_time_window_days,
            )
            validated.append(validated_event)
            pool.append(validated_event)

        return validated

    # ---------------------------------------------------------------------
    # Stage 1: Source-based initial confidence
    # ---------------------------------------------------------------------
    def _calculate_initial_confidence(self, event: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
        sources = event.get("sources") or []
        if not sources:
            return self.source_weights["unknown"], [{"source": "unknown", "weight": self.source_weights["unknown"]}]

        weights = []
        breakdown = []
        for source in sources:
            weight = self._resolve_source_weight(source)
            weights.append(weight)
            breakdown.append(
                {
                    "source": source.get("source") or source.get("name") or "unknown",
                    "type": source.get("type", "UNKNOWN"),
                    "weight": round(weight, 4),
                }
            )

        # Independent accumulation model: C0 = 1 - Π(1 - wi)
        product = 1.0
        for w in weights:
            product *= (1.0 - self._clamp(w))
        confidence = 1.0 - product
        return self._clamp(confidence), breakdown

    def _resolve_source_weight(self, source: Dict[str, Any]) -> float:
        source_name = (source.get("source") or source.get("name") or "").lower()
        source_type = (source.get("type") or "").lower()

        if "official" in source_name or source_type in {"official", "club_official"}:
            return self.source_weights["official"]
        if "romano" in source_name or "fabrizio" in source_name:
            return self.source_weights["romano"]
        if "sky sports" in source_name:
            return self.source_weights["sky_sports"]
        if "blog" in source_name or source_type in {"blog", "personal"}:
            return self.source_weights["blog"]
        if source_type in {"media", "news"}:
            return self.source_weights["media"]

        return self.source_weights["unknown"]

    # ---------------------------------------------------------------------
    # Stage 2: Candidate filtering + relation scoring
    # ---------------------------------------------------------------------
    def _select_candidates(self, event: Dict[str, Any], existing_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        candidates = []
        for item in existing_events:
            if not item.get("event_id"):
                continue

            participant_hit = self._participant_overlap(event, item) > 0.0
            time_hit = self._time_overlap(event, item) > 0.0
            title_hit = self._title_anchor_match(event, item)

            if participant_hit or time_hit or title_hit:
                candidates.append(item)

        return candidates

    def _same_event_slot(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """(EventType, Actor, Context, TimeScope) slot compatibility check."""
        type_a = self._event_type(a)
        type_b = self._event_type(b)
        if type_a != type_b:
            return False

        actor_overlap = self._participant_overlap(a, b)
        if actor_overlap <= 0.0:
            return False

        context_overlap = self._context_similarity(a, b)
        if context_overlap < 0.2:
            return False

        time_overlap = self._time_overlap(a, b)
        if time_overlap <= 0.0:
            return False

        return True

    def _support_score(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        p = self._participant_overlap(a, b)
        action = self._action_similarity(a, b)
        t = self._time_overlap(a, b)
        return self._clamp(0.4 * p + 0.4 * action + 0.2 * t)

    def _conflict_score(self, a: Dict[str, Any], b: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        negation = self._negation_conflict(a, b)
        numeric = self._numeric_conflict(a, b)
        unique = self._uniqueness_conflict(a, b)
        score = min(0.7 * negation + 0.6 * numeric + 0.6 * unique, 1.0)
        signals = {
            "negation": round(negation, 4),
            "numeric": round(numeric, 4),
            "uniqueness": round(unique, 4),
        }
        return self._clamp(score), signals

    # ---------------------------------------------------------------------
    # Stage 3: Bidirectional confidence propagation
    # ---------------------------------------------------------------------
    def _propagate_confidence(
        self,
        c_new: float,
        c_old: float,
        support_score: float,
        conflict_score: float,
    ) -> Dict[str, float]:
        before_new = self._clamp(c_new)
        before_old = self._clamp(c_old)
        new_conf = before_new
        old_conf = before_old

        if support_score >= self.support_threshold:
            # C_new+ = C_new + α S C_old (1 - C_new)
            # C_old+ = C_old + α S C_new (1 - C_old)
            new_conf = self._clamp(before_new + self.alpha * support_score * before_old * (1.0 - before_new))
            old_conf = self._clamp(before_old + self.alpha * support_score * before_new * (1.0 - before_old))

        if conflict_score >= self.conflict_threshold:
            # High-confidence suppresses low-confidence.
            if new_conf > old_conf:
                old_conf = self._clamp(old_conf - self.beta * conflict_score * new_conf * old_conf)
            else:
                new_conf = self._clamp(new_conf - self.beta * conflict_score * old_conf * new_conf)

        return {
            "before_new": before_new,
            "before_old": before_old,
            "new_confidence": new_conf,
            "old_confidence": old_conf,
        }

    # ---------------------------------------------------------------------
    # Scoring primitives
    # ---------------------------------------------------------------------
    def _participant_overlap(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        names_a = self._participant_names(a)
        names_b = self._participant_names(b)
        if not names_a or not names_b:
            return 0.0
        inter = len(names_a & names_b)
        union = len(names_a | names_b)
        return inter / union if union else 0.0

    def _action_similarity(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        constraints_a = self._constraint_types(a)
        constraints_b = self._constraint_types(b)

        if constraints_a and constraints_b:
            inter = len(constraints_a & constraints_b)
            union = len(constraints_a | constraints_b)
            constraint_sim = inter / union if union else 0.0
        else:
            constraint_sim = 0.0

        fact_type_sim = 1.0 if (a.get("fact_type") and a.get("fact_type") == b.get("fact_type")) else 0.0
        lexical_sim = self._text_jaccard(
            a.get("event_description", ""),
            b.get("event_description", ""),
        )

        # Weighted blend for behavior/action match.
        return self._clamp(0.5 * constraint_sim + 0.3 * fact_type_sim + 0.2 * lexical_sim)

    def _time_overlap(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        time_a = self._extract_time_scope(a)
        time_b = self._extract_time_scope(b)
        if not time_a or not time_b:
            return 0.0

        start_a, end_a = time_a
        start_b, end_b = time_b

        if start_a <= end_b and start_b <= end_a:
            overlap_start = max(start_a, start_b)
            overlap_end = min(end_a, end_b)
            overlap_days = (overlap_end - overlap_start).days + 1
            total_days = max((max(end_a, end_b) - min(start_a, start_b)).days + 1, 1)
            return overlap_days / total_days

        # Not overlapping ranges, use temporal distance decay.
        days = abs((start_a - start_b).days)
        if days <= 1:
            return 0.8
        if days <= 3:
            return 0.6
        if days <= 7:
            return 0.4
        if days <= self.candidate_time_window_days:
            return 0.2
        return 0.0

    def _negation_conflict(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        neg_words = {"not", "no", "never", "without", "denied", "deny", "否认", "未", "没有"}
        text_a = (a.get("event_description") or "").lower()
        text_b = (b.get("event_description") or "").lower()

        has_neg_a = any(w in text_a for w in neg_words)
        has_neg_b = any(w in text_b for w in neg_words)
        if has_neg_a == has_neg_b:
            return 0.0

        lexical = self._text_jaccard(text_a, text_b)
        return 1.0 if lexical >= 0.2 else 0.5

    def _numeric_conflict(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        nums_a = self._extract_numbers(a.get("event_description", ""))
        nums_b = self._extract_numbers(b.get("event_description", ""))
        if not nums_a or not nums_b:
            return 0.0

        inter = nums_a & nums_b
        if inter:
            return 0.0

        lexical = self._text_jaccard(a.get("event_description", ""), b.get("event_description", ""))
        return 1.0 if lexical >= 0.25 else 0.4

    def _uniqueness_conflict(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        text_a = (a.get("event_description") or "").lower()
        text_b = (b.get("event_description") or "").lower()

        exclusive_groups = [
            {"won", "lost", "drew"},
            {"signed", "rejected", "refused"},
            {"appointed", "sacked", "left"},
        ]

        for group in exclusive_groups:
            hit_a = {k for k in group if k in text_a}
            hit_b = {k for k in group if k in text_b}
            if hit_a and hit_b and hit_a != hit_b:
                return 1.0

        return 0.0

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _participant_names(self, event: Dict[str, Any]) -> set[str]:
        participants = event.get("participants") or []
        names = set()
        for p in participants:
            name = p.get("name")
            if name:
                names.add(str(name).strip().lower())
        return names

    def _constraint_types(self, event: Dict[str, Any]) -> set[str]:
        constraints = event.get("constraints") or []
        return {
            str(c.get("type", "")).strip().upper()
            for c in constraints
            if c.get("type")
        }

    def _title_anchor_match(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        title_a = (a.get("title_anchors") or "").strip().lower()
        title_b = (b.get("title_anchors") or "").strip().lower()
        return bool(title_a and title_b and title_a == title_b)

    def _event_type(self, event: Dict[str, Any]) -> str:
        constraints = sorted(self._constraint_types(event))
        if constraints:
            return constraints[0]
        return str(event.get("fact_type", "UNKNOWN")).upper()

    def _context_similarity(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        title_sim = 1.0 if self._title_anchor_match(a, b) else 0.0
        text_sim = self._text_jaccard(
            a.get("event_description", ""),
            b.get("event_description", ""),
        )
        return self._clamp(0.6 * title_sim + 0.4 * text_sim)

    def _extract_time_scope(self, event: Dict[str, Any]) -> Optional[Tuple[datetime, datetime]]:
        temporal = event.get("temporal_anchors") or []
        if temporal:
            first = temporal[0]
            event_date = self._parse_date(first.get("event_date"))
            valid_from = self._parse_date(first.get("valid_from"))
            valid_to = self._parse_date(first.get("valid_to"))

            if event_date:
                return event_date, event_date
            if valid_from and valid_to:
                return min(valid_from, valid_to), max(valid_from, valid_to)
            if valid_from:
                return valid_from, valid_from
            if valid_to:
                return valid_to, valid_to

        # fallback to publish date if exists
        publish_date = self._parse_date(event.get("publish_date"))
        if publish_date:
            return publish_date, publish_date
        return None

    def _parse_date(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value

        text = str(value).strip()
        if not text:
            return None

        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                dt = datetime.strptime(text, fmt)
                return dt
            except ValueError:
                continue
        return None

    def _text_jaccard(self, a: str, b: str) -> float:
        tokens_a = self._tokenize(a)
        tokens_b = self._tokenize(b)
        if not tokens_a or not tokens_b:
            return 0.0
        inter = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return inter / union if union else 0.0

    def _tokenize(self, text: str) -> set[str]:
        words = re.findall(r"[A-Za-z0-9]+", (text or "").lower())
        stop = {"the", "a", "an", "of", "to", "in", "on", "and", "for", "with"}
        return {w for w in words if len(w) > 1 and w not in stop}

    def _extract_numbers(self, text: str) -> set[str]:
        # captures integers/decimals and common score patterns like 2-1
        values = set(re.findall(r"\d+(?:\.\d+)?", text or ""))
        score_patterns = re.findall(r"\b\d+\s*[-:]\s*\d+\b", text or "")
        values.update(v.replace(" ", "") for v in score_patterns)
        return values

    def _safe_confidence(self, event: Dict[str, Any]) -> float:
        if isinstance(event.get("validation"), dict):
            val_conf = event["validation"].get("current_confidence")
            if val_conf is not None:
                return self._clamp(float(val_conf))

        score = event.get("confidence_score")
        if score is not None:
            try:
                return self._clamp(float(score))
            except (TypeError, ValueError):
                pass

        initial, _ = self._calculate_initial_confidence(event)
        return initial

    def _resolve_status(self, confidence: float) -> str:
        if confidence >= self.acceptance_threshold:
            return "accepted"
        if confidence >= self.review_threshold:
            return "needs_review"
        return "rejected"

    def _clamp(self, value: float) -> float:
        if math.isnan(value):
            return 0.0
        return max(0.0, min(1.0, value))
