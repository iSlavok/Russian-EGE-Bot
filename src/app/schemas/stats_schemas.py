from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


class ProfileSummaryDTO(BaseModel):
    full_name: str
    registered_at: datetime
    total_answered: int
    total_correct: int
    correct_percent: int
    current_streak: int
    max_streak: int
    current_daily_streak: int


class CategoryStatItemDTO(BaseModel):
    category_id: int
    name: str
    is_ege_task: bool
    total_answered: int
    total_correct: int
    percent: int
