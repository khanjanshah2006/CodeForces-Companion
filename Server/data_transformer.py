"""
data_transformer.py
===================
Data Transformation Service for the Codeforces Companion Platform.

This module ingests raw Codeforces API payloads and processes them through a
highly optimised O(N) single-pass state machine, producing three strongly-typed
data contracts consumed by downstream services:

    1. AnalyticsSummaryResponse  – powers the Analytics Dashboard
    2. POTDContextResponse        – drives the Problem of the Day engine
    3. RoadmapContextResponse     – provides context for the AI Roadmap Builder

Architecture: Hybrid Deterministic + Probabilistic
    - All counting, de-duplication, thresholding, and sorting happen here in
      Python (deterministic, < 2ms, 95% token reduction for LLM calls).
    - Contextual reasoning and curriculum synthesis are delegated to the
      generative AI layer via the compressed payloads produced here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Global Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global Configuration & Domain Constants
# ---------------------------------------------------------------------------

ALL_CODEFORCES_TAGS: Set[str] = {
    "2-sat",
    "binary search",
    "bitmasks",
    "brute force",
    "chinese remainder theorem",
    "combinatorics",
    "constructive algorithms",
    "data structures",
    "dfs and similar",
    "divide and conquer",
    "dp",
    "dsu",
    "expression parsing",
    "fft",
    "flows",
    "games",
    "geometry",
    "graph matchings",
    "graphs",
    "greedy",
    "hashing",
    "implementation",
    "interactive",
    "math",
    "matrices",
    "meet-in-the-middle",
    "number theory",
    "probabilities",
    "schedules",
    "shortest paths",
    "sortings",
    "string suffix structures",
    "strings",
    "ternary search",
    "trees",
    "two pointers",
}

# Placeholder tags returned when the user has insufficient submission history.
_FUNDAMENTAL_TAGS: List[str] = ["implementation", "brute force", "math"]

# Minimum unique problem attempts required to verify true topic mastery
MIN_VOLUME_THRESHOLD: int = 10

# ---------------------------------------------------------------------------
# Output Data Contracts (Pydantic Models)
# ---------------------------------------------------------------------------


class AnalyticsSummaryResponse(BaseModel):
    """
    Data contract for the Analytics Dashboard.

    Encapsulates rating info, overall acceptance rate, the most common error
    verdict, per-rating solve counts, and the skill-strength/weakness profile.
    """

    handle: str = Field(..., description="Codeforces handle of the user")
    current_rating: int = Field(..., description="Current Codeforces rating")
    max_rating: int = Field(..., description="Peak Codeforces rating")
    rank: str = Field(..., description="Current rank string (e.g. 'specialist')")
    overall_acceptance_rate: float = Field(
        ...,
        description="Fraction of total submissions that received an OK verdict",
    )
    top_issue_verdict: str = Field(
        ...,
        description="Non-OK verdict with the highest absolute submission count",
    )
    problems_solved_by_rating: Dict[int, int] = Field(
        ...,
        description="Map of problem difficulty rating → unique solved problem count",
    )
    weak_tags: List[Dict[str, Any]] = Field(
        ...,
        description="Top-5 tags sorted by highest unique failure index (descending)",
    )
    strong_tags: List[Dict[str, Any]] = Field(
        ...,
        description="Top-5 tags sorted by lowest unique failure index (ascending)",
    )
    untried_tags: List[str] = Field(
        ...,
        description="Tags present in ALL_CODEFORCES_TAGS that were never attempted",
    )
    unsolved_problems: List[Dict[str, Any]] = Field(
        default=[],
        description="Top-10 unsolved problems that have failed attempts but are still unsolved"
    )


class POTDContextResponse(BaseModel):
    """
    Data contract for the Problem of the Day (POTD) Engine.

    Provides the minimal, high-signal payload needed for real-time problem
    selection and exclusion filtering.
    """

    current_rating: int = Field(..., description="Current Codeforces rating")
    target_training_load: Dict[str, List[str]] = Field(
        ...,
        description=(
            "Categorised tag groups following the 50-30-20 learning balance rule. "
            "Keys: 'core_focus' (50%), 'breadth_maintenance' (30%), "
            "'conditioning_speed' (20%)"
        ),
    )
    solved_problem_ids: Set[str] = Field(
        ...,
        description=(
            "Unique problem IDs in 'contestId+index' format (e.g. '1520F') "
            "that the user has already solved — used as an absolute exclusion filter"
        ),
    )
    failed_problem_ids: Set[str] = Field(
        ...,
        description=(
            "Unique problem IDs attempted but never passed — candidates for "
            "retry scheduling"
        ),
    )

    class Config:
        # Allow Set fields to serialise correctly
        json_encoders = {set: list}


class RoadmapContextResponse(BaseModel):
    """
    Data contract for the AI-driven Personalised Roadmap Builder.

    Provides a compressed, semantically rich payload for downstream LLM
    prompt contextualisation.
    """

    current_rating: int = Field(..., description="Current Codeforces rating")
    target_rating_goal: Optional[int] = Field(
        None, description="User-supplied target rating (optional)"
    )
    primary_weakness: str = Field(
        ...,
        description="The single tag with the highest unique failure index",
    )
    top_issue_verdict: str = Field(
        ...,
        description="Non-OK verdict with the highest absolute submission count",
    )
    learning_matrix_profile: Dict[str, Any] = Field(
        ...,
        description=(
            "Aggregated tag profiles including attempt counts, solve counts, "
            "failure index, and recommended difficulty ranges for LLM injection"
        ),
    )


# ---------------------------------------------------------------------------
# Internal Helper Types
# ---------------------------------------------------------------------------


class _ProblemState:
    """
    Lightweight internal state object for a single unique problem encountered
    during the single-pass iteration.
    """

    __slots__ = ("solved", "rating", "tags", "failed_attempts", "title", "contest_id", "index")

    def __init__(self) -> None:
        self.solved: bool = False
        self.rating: Optional[int] = None
        self.tags: List[str] = []
        self.failed_attempts: int = 0
        self.title: str = ""
        self.contest_id: Optional[int] = None
        self.index: str = ""


class _TagAggregate:
    """
    Accumulates per-tag statistics across the entire submission history.
    Uses sets for unique problem tracking to enable O(1) deduplication.
    """

    __slots__ = ("unique_attempted", "unique_solved", "raw_failures")

    def __init__(self) -> None:
        self.unique_attempted: Set[str] = set()
        self.unique_solved: Set[str] = set()
        self.raw_failures: int = 0


# ---------------------------------------------------------------------------
# Core Processor
# ---------------------------------------------------------------------------


class CodeforcesDataProcessor:
    """
    High-performance data transformation engine.

    Ingests the raw Codeforces `user.status` response alongside basic profile
    data, and produces three distinct, typed data contracts via a single O(N)
    pass over the submission history.

    Usage
    -----
    processor = CodeforcesDataProcessor(
        handle="tourist",
        current_rating=3522,
        max_rating=3979,
        rank="legendary grandmaster",
    )
    analytics, potd, roadmap = processor.process_submissions(
        submissions=raw_user_status_result,
        target_rating_goal=3600,
    )
    """

    def __init__(
        self,
        handle: str,
        current_rating: int,
        max_rating: int,
        rank: str,
    ) -> None:
        self.handle = handle
        self.current_rating = current_rating
        self.max_rating = max_rating
        self.rank = rank

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_submissions(
        self,
        submissions: List[Dict[str, Any]],
        target_rating_goal: Optional[int] = None,
    ) -> tuple[AnalyticsSummaryResponse, POTDContextResponse, RoadmapContextResponse]:
        """
        Execute the full transformation pipeline over a raw submission list.

        Parameters
        ----------
        submissions:
            The ``result`` array from a Codeforces ``user.status`` API call.
        target_rating_goal:
            Optional user-supplied target rating forwarded to the Roadmap contract.

        Returns
        -------
        (AnalyticsSummaryResponse, POTDContextResponse, RoadmapContextResponse)
        """

        # ---------------------------------------------------------------
        # Phase 1: In-Memory Data Structure Initialisation
        # ---------------------------------------------------------------
        # problem_states  – tracks unique problems by their composite key
        problem_states: Dict[str, _ProblemState] = {}

        # tag_aggregates  – accumulates per-tag analytical metrics
        tag_aggregates: Dict[str, _TagAggregate] = {}

        # verdict_counts  – fast accumulator for raw verdict frequencies
        verdict_counts: Dict[str, int] = {}

        total_submissions: int = 0

        # ---------------------------------------------------------------
        # Phase 2: Core O(N) Single-Pass Optimisation Loop
        # ---------------------------------------------------------------
        for submission in submissions:
            total_submissions += 1

            # -- 2a. Unique Key Generation --
            # Combine contestId and problem index into a canonical ID string
            # e.g. contestId=1520, index="F"  →  "1520F"
            contest_id = submission.get("contestId", "")
            problem_node = submission.get("problem", {})
            problem_index = problem_node.get("index", "")
            problem_id: str = str(contest_id) + str(problem_index)

            verdict: str = submission.get("verdict", "") or ""

            # -- 2b. Verdict Accumulation (O(1) hash map increment) --
            if verdict:
                verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

            # -- 2c. Deduplication State Resolution --
            if problem_id not in problem_states:
                # First time we see this problem — initialise its state block.
                state = _ProblemState()
                # Defensive safe lookups for optional metadata fields (Edge Case §3)
                state.rating = problem_node.get("rating")          # may be None
                state.tags = problem_node.get("tags") or []        # may be absent
                state.title = problem_node.get("name", "")
                state.contest_id = problem_node.get("contestId")
                state.index = problem_node.get("index", "")
                problem_states[problem_id] = state
            else:
                state = problem_states[problem_id]

            if verdict == "OK":
                # Permanently mark this problem as solved regardless of
                # submission order (idempotent flag mutation).
                state.solved = True
            elif verdict:
                # Always increment failures to track historical struggle,
                # even if they eventually solved it (Codeforces returns
                # submissions newest-first, so a solved state may already be
                # set when we encounter an older failing attempt).
                state.failed_attempts += 1

            # -- 2d. Tag Multi-Mapping Acceleration --
            # Every tag on the problem receives an update in the aggregation map.
            for tag in state.tags:
                if tag not in tag_aggregates:
                    tag_aggregates[tag] = _TagAggregate()

                agg = tag_aggregates[tag]
                agg.unique_attempted.add(problem_id)

                if verdict == "OK":
                    agg.unique_solved.add(problem_id)
                elif verdict:
                    agg.raw_failures += 1

        # ---------------------------------------------------------------
        # Cold Start Guard (Edge Case §1)
        # If fewer than 5 unique problems have been attempted the data is
        # statistically insufficient for ranking.  Return placeholder data.
        # ---------------------------------------------------------------
        total_unique_problems = len(problem_states)

        if total_unique_problems < 5:
            logger.warning(
                "Cold-start guard triggered for handle '%s': only %d unique "
                "problem(s) found (minimum 5 required).",
                self.handle,
                total_unique_problems,
            )
            return self._build_cold_start_response(
                target_rating_goal=target_rating_goal,
                verdict_counts=verdict_counts,
                total_submissions=total_submissions,
            )

        # ---------------------------------------------------------------
        # Phase 3: Mathematical Post-Processing & Normalisation
        # ---------------------------------------------------------------

        # -- 3a. Failure Index Calculation --
        # Drop any tag with fewer than 3 unique problem attempts (noise filter).
        tag_failure_data: List[Dict[str, Any]] = []

        for tag, agg in tag_aggregates.items():
            n_attempted = len(agg.unique_attempted)
            if n_attempted < 3:
                continue  # insufficient data — skip this tag

            n_solved = len(agg.unique_solved)

            # Zero-Division Firewall (Edge Case §2): denominator guaranteed > 0
            # by the n_attempted >= 3 guard above, but we verify explicitly.
            failure_index: float = (
                1.0 - (n_solved / n_attempted) if n_attempted > 0 else 0.0
            )

            tag_failure_data.append(
                {
                    "tag": tag,
                    "failure_index": round(failure_index, 4),
                    "unique_attempted": n_attempted,
                    "unique_solved": n_solved,
                    "raw_failures": agg.raw_failures,
                }
            )

        # -- 3b. Weak & Strong Tag Extraction --
        # weak_tags  : descending failure index  (hardest tags for the user)
        # strong_tags: ascending failure index   (most comfortable tags)
        weak_tags_sorted = sorted(
            tag_failure_data, key=lambda d: d["failure_index"], reverse=True
        )
        strong_tags_sorted = sorted(
            tag_failure_data, key=lambda d: d["failure_index"]
        )

        weak_tags_top5 = weak_tags_sorted[:5]
        strong_tags_top5 = strong_tags_sorted[:5]

        # -- 3c. Untried Tags --
        tried_tags: Set[str] = set(tag_aggregates.keys())
        untried_tags: List[str] = sorted(ALL_CODEFORCES_TAGS - tried_tags)

        # -- 3d. Problems Solved by Rating --
        problems_solved_by_rating: Dict[int, int] = {}
        for pid, state in problem_states.items():
            if state.solved and state.rating is not None:
                rating_bucket = state.rating
                problems_solved_by_rating[rating_bucket] = (
                    problems_solved_by_rating.get(rating_bucket, 0) + 1
                )

        # -- 3e. Solved & Failed Problem ID Sets --
        solved_problem_ids: Set[str] = set()
        failed_problem_ids: Set[str] = set()
        for pid, state in problem_states.items():
            if state.solved:
                solved_problem_ids.add(pid)
            elif state.failed_attempts > 0:
                # Attempted at least once but never passed
                failed_problem_ids.add(pid)

        # -- 3f. Overall Acceptance Rate --
        ok_count = verdict_counts.get("OK", 0)
        # Zero-Division Firewall: check total_submissions before dividing
        overall_acceptance_rate: float = (
            ok_count / total_submissions if total_submissions > 0 else 0.0
        )

        # -- 3g. Top Issue Verdict --
        # Find the non-OK verdict with the highest absolute count
        top_issue_verdict = self._compute_top_issue(verdict_counts)

        # ---------------------------------------------------------------
        # 50-30-20 Learning Balance Allocation
        # ---------------------------------------------------------------
        target_training_load = self._build_training_load(
            weak_tags_sorted=weak_tags_sorted,
            strong_tags_sorted=strong_tags_sorted,
            tag_failure_data=tag_failure_data,
        )

        # ---------------------------------------------------------------
        # Learning Matrix Profile (for Roadmap LLM context)
        # ---------------------------------------------------------------
        learning_matrix_profile = self._build_learning_matrix(
            target_training_load=target_training_load,
            tag_failure_data=tag_failure_data,
        )

        primary_weakness = (
            weak_tags_sorted[0]["tag"] if weak_tags_sorted else _FUNDAMENTAL_TAGS[0]
        )

        # -- 3h. Unsolved Problems --
        unsolved_problems_list = []
        for pid, state in problem_states.items():
            if not state.solved and state.failed_attempts > 0:
                unsolved_problems_list.append({
                    "problem_id": pid,
                    "title": state.title,
                    "rating": state.rating,
                    "tags": state.tags,
                    "failed_attempts": state.failed_attempts,
                    "contest_id": state.contest_id,
                    "index": state.index
                })
        unsolved_problems_list.sort(key=lambda x: x["failed_attempts"], reverse=True)
        unsolved_problems_top10 = unsolved_problems_list[:10]

        # ---------------------------------------------------------------
        # Assemble Data Contracts
        # ---------------------------------------------------------------
        analytics = AnalyticsSummaryResponse(
            handle=self.handle,
            current_rating=self.current_rating,
            max_rating=self.max_rating,
            rank=self.rank,
            overall_acceptance_rate=round(overall_acceptance_rate, 4),
            top_issue_verdict=top_issue_verdict,
            problems_solved_by_rating=dict(
                sorted(problems_solved_by_rating.items())
            ),
            weak_tags=weak_tags_top5,
            strong_tags=strong_tags_top5,
            untried_tags=untried_tags,
            unsolved_problems=unsolved_problems_top10,
        )

        potd = POTDContextResponse(
            current_rating=self.current_rating,
            target_training_load=target_training_load,
            solved_problem_ids=solved_problem_ids,
            failed_problem_ids=failed_problem_ids,
        )

        roadmap = RoadmapContextResponse(
            current_rating=self.current_rating,
            target_rating_goal=target_rating_goal,
            primary_weakness=primary_weakness,
            top_issue_verdict=top_issue_verdict,
            learning_matrix_profile=learning_matrix_profile,
        )

        return analytics, potd, roadmap

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_top_issue(verdict_counts: Dict[str, int]) -> str:
        """
        Return the non-OK verdict with the highest absolute submission count.
        Falls back to 'N/A' if no non-OK verdicts exist.
        """
        non_ok = {k: v for k, v in verdict_counts.items() if k != "OK"}
        if not non_ok:
            return "N/A"
        return max(non_ok, key=lambda k: non_ok[k])

    @staticmethod
    def _build_training_load(
        weak_tags_sorted: List[Dict[str, Any]],
        strong_tags_sorted: List[Dict[str, Any]],
        tag_failure_data: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """
        Partition tags into 50/30/20 buckets using a 2D Volume-Failure Matrix.
        Intercepts low-volume/high-accuracy tags and pushes them to breadth_maintenance.
        """
        # 1. Extract Core Focus (Top 5 weak tags)
        core_focus = [d["tag"] for d in weak_tags_sorted[:5]]

        # 2. Extract Conditioning Pool, filtering out the Overconfidence Trap
        conditioning = []
        under_explored = []

        for d in strong_tags_sorted:
            if len(conditioning) >= 3:
                break
            if d["tag"] in core_focus:
                continue
                
            # Check 2D Matrix constraint: low failure rate but insufficient exposure
            if d["unique_attempted"] < MIN_VOLUME_THRESHOLD:
                under_explored.append(d["tag"])
            else:
                conditioning.append(d["tag"])

        # 3. Extract Breadth & Maintenance (mid-tier tags + re-routed under-explored tags)
        allocated = set(core_focus) | set(conditioning)
        
        # Pull typical mid-tier failure tags
        standard_breadth = [
            d["tag"]
            for d in tag_failure_data
            if d["tag"] not in allocated
            and d["tag"] not in under_explored
            and 0.25 <= d["failure_index"] <= 0.75
        ]

        # Combine under-explored tags at the front of breadth to prioritize depth testing
        breadth = (under_explored + standard_breadth)[:4]

        # Fallback to fundamentals if breadth remains empty
        if not breadth:
            breadth = [t for t in _FUNDAMENTAL_TAGS if t not in allocated]

        return {
            "core_focus": core_focus,
            "breadth_maintenance": breadth,
            "conditioning_speed": conditioning,
        }

    def _build_learning_matrix(
        self,
        target_training_load: Dict[str, List[str]],
        tag_failure_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build the rich learning matrix payload for LLM roadmap injection.
        Dynamically annotates under-explored tags with an elevated difficulty baseline.
        """
        r = self.current_rating

        def get_tag_dicts(tag_names: List[str]) -> List[Dict[str, Any]]:
            return [d for d in tag_failure_data if d["tag"] in tag_names]

        # Process Core Focus (Weaknesses)
        core_focus_tags = [
            {
                **t,
                "recommended_difficulty_low": r + 100,
                "recommended_difficulty_high": r + 200,
                "status": "systemic_weakness"
            }
            for t in get_tag_dicts(target_training_load["core_focus"])
        ]

        # Process Breadth & Maintenance, adjusting for the low-volume intercept
        maintenance_tags = []
        for t in get_tag_dicts(target_training_load["breadth_maintenance"]):
            is_under_explored = t["unique_attempted"] < MIN_VOLUME_THRESHOLD
            maintenance_tags.append({
                **t,
                # Force an on-level or slightly elevated challenge to test depth
                "recommended_difficulty_low": r + (50 if is_under_explored else 0),
                "recommended_difficulty_high": r + (100 if is_under_explored else 0),
                "status": "under_explored_needs_depth" if is_under_explored else "maintenance"
            })

        # Process Conditioning (True Mastery)
        conditioning_tags = [
            {
                **t,
                "recommended_difficulty_low": r - 200,
                "recommended_difficulty_high": r - 100,
                "status": "true_mastering"
            }
            for t in get_tag_dicts(target_training_load["conditioning_speed"])
        ]

        return {
            "core_focus_tags": core_focus_tags,
            "maintenance_tags": maintenance_tags,
            "conditioning_tags": conditioning_tags,
        }

    def _build_cold_start_response(
        self,
        target_rating_goal: Optional[int],
        verdict_counts: Dict[str, int],
        total_submissions: int,
    ) -> tuple[AnalyticsSummaryResponse, POTDContextResponse, RoadmapContextResponse]:
        """
        Fallback path for users with fewer than 5 unique problem attempts.

        Returns placeholder contracts populated with platform fundamentals and
        marks analytical fields as 'insufficient_data' where applicable.
        """
        top_issue = self._compute_top_issue(verdict_counts)
        ok_count = verdict_counts.get("OK", 0)
        acceptance_rate = (
            ok_count / total_submissions if total_submissions > 0 else 0.0
        )

        placeholder_tags = [
            {
                "tag": t,
                "failure_index": 0.0,
                "unique_attempted": 0,
                "unique_solved": 0,
                "raw_failures": 0,
                "status": "insufficient_data",
            }
            for t in _FUNDAMENTAL_TAGS
        ]

        analytics = AnalyticsSummaryResponse(
            handle=self.handle,
            current_rating=self.current_rating,
            max_rating=self.max_rating,
            rank=self.rank,
            overall_acceptance_rate=round(acceptance_rate, 4),
            top_issue_verdict=top_issue,
            problems_solved_by_rating={},
            weak_tags=placeholder_tags,
            strong_tags=placeholder_tags,
            untried_tags=sorted(ALL_CODEFORCES_TAGS),
            unsolved_problems=[],
        )

        training_load: Dict[str, List[str]] = {
            "core_focus": _FUNDAMENTAL_TAGS[:],
            "breadth_maintenance": _FUNDAMENTAL_TAGS[:],
            "conditioning_speed": _FUNDAMENTAL_TAGS[:],
        }

        potd = POTDContextResponse(
            current_rating=self.current_rating,
            target_training_load=training_load,
            solved_problem_ids=set(),
            failed_problem_ids=set(),
        )

        r = self.current_rating
        roadmap = RoadmapContextResponse(
            current_rating=r,
            target_rating_goal=target_rating_goal,
            primary_weakness=_FUNDAMENTAL_TAGS[0],
            top_issue_verdict=top_issue,
            learning_matrix_profile={
                "status": "insufficient_data",
                "core_focus_tags": [
                    {
                        "tag": t,
                        "recommended_difficulty_low": r + 100,
                        "recommended_difficulty_high": r + 200,
                    }
                    for t in _FUNDAMENTAL_TAGS
                ],
                "maintenance_tags": [],
                "conditioning_tags": [],
            },
        )

        return analytics, potd, roadmap
