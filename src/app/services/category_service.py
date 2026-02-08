from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import CategoryNotFoundError
from app.repositories import CategoryRepository
from app.schemas import CategoryDTO, CategoryWithChildrenDTO


class CategoryService:
    def __init__(self, session: AsyncSession, category_repository: CategoryRepository) -> None:
        self._session = session
        self._category_repository = category_repository

    async def get_root_categories(self) -> list[CategoryDTO]:
        categories = await self._category_repository.get_roots()
        return [
            CategoryDTO.from_orm_obj(category)
            for category in categories
        ]

    async def get_by_id_with_children(self, category_id: int) -> CategoryWithChildrenDTO:
        category = await self._category_repository.get_by_id_with_children(category_id)
        if category is None:
            raise CategoryNotFoundError(category_id)
        return CategoryWithChildrenDTO.from_orm_obj(category)

    async def get_by_id_with_tree(self, category_id: int) -> list[CategoryDTO]:
        categories = await self._category_repository.get_by_id_with_tree(category_id)
        if not categories:
            raise CategoryNotFoundError(category_id)
        return [
            CategoryDTO.from_orm_obj(category)
            for category in categories
        ]
