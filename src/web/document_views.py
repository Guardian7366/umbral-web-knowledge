"""Shared category labels for document presentation."""

from __future__ import annotations

CATEGORY_LABELS = {
    "design_references": "Design references",
    "creative_methods": "Creative methods",
    "project_lessons": "Project lessons",
}


def category_label(category: str) -> str:
    """Return a readable category name."""

    return CATEGORY_LABELS.get(
        category,
        category.replace("_", " ").title(),
    )
