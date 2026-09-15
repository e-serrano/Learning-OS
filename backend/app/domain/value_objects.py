"""Constrained numeric ranges shared across domain entities.

See docs/DOMAIN_MODEL.md #1 ("mastery 0..5, confidence/retention 0..100,
importance/difficulty 1..5") and docs/SPECS.md #7. Values outside range
raise pydantic.ValidationError at construction time.
"""

from typing import Annotated

from pydantic import Field

Mastery = Annotated[float, Field(ge=0, le=5)]
"""Concept/Skill mastery, 0..5 -- see docs/DOMAIN_MODEL.md #4, #5."""

ConfidencePercent = Annotated[float, Field(ge=0, le=100)]
"""User-reported/inferred confidence as a percentage, 0..100."""

RetentionPercent = Annotated[float, Field(ge=0, le=100)]
"""Retention as a percentage, 0..100 -- see docs/DOMAIN_MODEL.md #4."""

NormalizedScore = Annotated[float, Field(ge=0, le=1)]
"""Evidence/Evaluation dimension scores, normalized 0..1 -- see #6, #9."""

FiveLevelScale = Annotated[int, Field(ge=1, le=5)]
"""Shared 1..5 integer scale: goal priority, concept importance, exercise/
project/assessment difficulty -- see docs/DOMAIN_MODEL.md #3, #4, #7, #14."""
