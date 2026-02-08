from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories import CategoryRepository, UserRepository
from app.schemas import CategoryDTO, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


class UserService:
    def __init__(
            self,
            session: AsyncSession,
            user_repository: UserRepository,
            category_repository: CategoryRepository,
    ) -> None:
        self._session = session
        self._user_repository = user_repository
        self._category_repository = category_repository

    async def get_user_by_id(self, user_id: int) -> User | None:
        user = await self._user_repository.get_by_id(user_id)
        if not user:
            logger.warning(f"User with ID {user_id} not found")
        return user

    async def get_user_by_telegram(
            self,
            telegram_id: int,
            tg_username: str | None,
            full_name: str,
    ) -> UserWithExercisesDTO:
        user = await self._user_repository.get_by_telegram_id_with_exercises(telegram_id)
        if user is None:
            user = await self.create_user(
                telegram_id=telegram_id,
                tg_username=tg_username,
                full_name=full_name,
            )
            return UserWithExercisesDTO.from_orm_obj(user, load_exercises=False, load_category=False)
        is_updated = False
        if user.username != tg_username:
            user.username = tg_username
            is_updated = True
        if user.full_name != full_name:
            user.full_name = full_name
            is_updated = True
        if is_updated:
            logger.info(f"Updated user with TG ID {telegram_id}")
            await self._session.commit()

        return UserWithExercisesDTO.from_orm_obj(user)

    async def create_user(
            self,
            telegram_id: int,
            tg_username: str | None,
            full_name: str,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=tg_username,
            full_name=full_name,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        logger.info(f"Created new user with TG ID {telegram_id}")
        return user

    async def select_category(self, user: UserWithCategoryDTO, category: CategoryDTO) -> None:
        db_user = await self._user_repository.get_by_id(user.id)
        if not db_user:
            msg = f"User with ID {user.id} not found"
            raise ValueError(msg)
        db_user.current_category_id = category.id
        await self._session.flush()

        user.current_category_id = category.id
        user.current_category = category

