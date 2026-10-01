import enum


class CaseStatus(str, enum.Enum):
    """A case only becomes usable once two independent reviewers agree."""

    DRAFT = "draft"
    NEEDS_RESOLUTION = "needs_resolution"  # reviewers disagreed -> ambiguous source
    APPROVED = "approved"
    RETIRED = "retired"


class CheckMode(str, enum.Enum):
    """Component check (frozen context) vs. end-to-end check (own retrieval)."""

    COMPONENT = "component"
    END_TO_END = "end_to_end"
    BOTH = "both"


class GraderType(str, enum.Enum):
    """Grading evolved from exact-match -> keyword -> LLM-as-judge+rubric."""

    EXACT_MATCH = "exact_match"
    KEYWORD = "keyword"
    LLM_JUDGE = "llm_judge"


class TriggerSource(str, enum.Enum):
    """The two overlapping triggers that make Measure continuous."""

    SCHEDULE = "schedule"
    ON_CHANGE = "on_change"
    MANUAL = "manual"


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    ERRORED = "errored"


class Diagnosis(str, enum.Enum):
    """When component passes but end-to-end fails on the same case."""

    UPSTREAM_RETRIEVAL_FAULT = "upstream_retrieval_fault"
    REASONING_FAULT = "reasoning_fault"
    NONE = "none"


class CoverageStatus(str, enum.Enum):
    """"If this broke silently, who would notice, and when?" """

    COVERED = "covered"
    PARTIAL = "partial"
    NONE = "none"


class AlertType(str, enum.Enum):
    PASS_RATE_DROP = "pass_rate_drop"
    NEW_FAILURE = "new_failure"
    CALIBRATION_STALE = "calibration_stale"
    COVERAGE_GAP_DUE = "coverage_gap_due"
