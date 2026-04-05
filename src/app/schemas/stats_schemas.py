from datetime import datetime

from pydantic import BaseModel


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
