from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPKMixin

DEFAULT_RUBRIC_DIMENSIONS = [
    {
        "key": "core_fact_correct",
        "description": "States the fact the case exists to check, accurately.",
    },
    {
        "key": "no_false_claims",
        "description": "Makes no incorrect claim, even outside the core fact.",
    },
    {
        "key": "no_unsafe_omission",
        "description": "Doesn't leave out information needed to act safely.",
    },
]


class Rubric(UUIDPKMixin, TimestampMixin, Base):
    """A structured set of separate yes/no questions a grader answers about
    one response, scored dimension by dimension instead of collapsed into a
    single blended verdict. A case passes only if every dimension passes."""

    __tablename__ = "rubrics"

    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    dimensions: Mapped[list[dict]] = mapped_column(JSON)
