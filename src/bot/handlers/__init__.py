from .category_handler import router as category_router
from .main_handler import router as main_router
from .task_handler import router as task_router

__all__ = [
    "category_router",
    "main_router",
    "task_router",
]
