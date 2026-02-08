from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category
from app.repositories import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Category)

    async def get_roots(self) -> Sequence[Category]:
        statement = (
            select(Category)
            .filter(Category.parent_id.is_(None))
            .order_by(Category.id.asc())
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_by_id_with_children(self, category_id: int) -> Category | None:
        statement = (
            select(Category)
            .filter_by(id=category_id)
            .options(selectinload(Category.children))
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_by_id_with_tree(self, category_id: int) -> Sequence[Category]:
        top_q = (
            select(Category)
            .filter_by(id=category_id)
            .cte("cte", recursive=True)
        )

        bottom_q = (
            select(Category)
            .join(
                top_q,
                Category.parent_id == top_q.c.id,
            )
        )

        recursive_q = top_q.union_all(bottom_q)

        statement = (
            select(Category)
            .from_statement(select(recursive_q))
        )

        result = await self.session.execute(statement)
        return result.scalars().all()
