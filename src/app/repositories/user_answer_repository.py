
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserAnswer
from app.repositories import BaseRepository


class UserAnswerRepository(BaseRepository[UserAnswer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserAnswer)
