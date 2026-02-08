from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import User
from app.repositories import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_telegram_id_with_exercises(self, telegram_id: int) -> User | None:
        statement = (
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(
                joinedload(User.current_category),
                selectinload(User.current_exercises),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id_with_exercises(self, user_id: int) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(
                joinedload(User.current_category),
                selectinload(User.current_exercises),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
