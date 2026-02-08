from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BaseDBModel


class BaseRepository[ModelType: BaseDBModel]:
    model: type[ModelType]

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(self, obj_id: int) -> ModelType | None:
        return await self.session.get(self.model, obj_id)

    def get_many_from_cache(self, obj_ids: Sequence[int]) -> list[ModelType]:
        results = []
        for obj_id in obj_ids:
            key = (self.model, (obj_id,), None)
            obj = self.session.identity_map.get(key)
            if obj is not None:
                results.append(obj)
        return results

    def add(self, db_obj: ModelType) -> None:
        self.session.add(db_obj)

    async def delete(self, db_obj: ModelType) -> None:
        await self.session.delete(db_obj)

    async def refresh(self, db_obj: ModelType) -> None:
        await self.session.refresh(db_obj)

    async def flush(self, db_objects: Sequence[ModelType] | ModelType | None = None) -> None:
        db_objects_seq = [db_objects] if db_objects is not None and not isinstance(db_objects, Sequence) else db_objects
        await self.session.flush(db_objects_seq)

    async def commit(self) -> None:
        await self.session.commit()
