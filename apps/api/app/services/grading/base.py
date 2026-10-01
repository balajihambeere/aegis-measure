from dataclasses import dataclass, field


@dataclass
class DimensionResult:
    passed: bool
    rationale: str = ""


@dataclass
class GradingResult:
    """A case passes only if every rubric dimension passes — a single
    blended yes/no verdict would let a judge quietly excuse a correct core
    fact sitting next to an invented or false detail."""

    passed: bool
    dimension_results: dict[str, DimensionResult] = field(default_factory=dict)

    def as_json(self) -> dict:
        return {
            key: {"passed": dim.passed, "rationale": dim.rationale}
            for key, dim in self.dimension_results.items()
        }
