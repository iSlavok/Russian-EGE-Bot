from pydantic import BaseModel

from app.enums import HandlerType
from app.models import Category


class CategoryDTO(BaseModel):
    id: int
    name: str
    handler_type: HandlerType | None
    parent_id: int | None
    is_ege_task: bool = False

    @classmethod
    def from_orm_obj(cls, orm_obj: Category) -> "CategoryDTO":
        return cls(
            id=orm_obj.id,
            name=orm_obj.name,
            handler_type=orm_obj.handler_type,
            parent_id=orm_obj.parent_id,
            is_ege_task=orm_obj.is_ege_task,
        )


class CategoryWithChildrenDTO(CategoryDTO):
    children: list["CategoryDTO"] = []

    @classmethod
    def from_orm_obj(cls, orm_obj: Category) -> "CategoryWithChildrenDTO":
        return cls(
            id=orm_obj.id,
            name=orm_obj.name,
            handler_type=orm_obj.handler_type,
            parent_id=orm_obj.parent_id,
            is_ege_task=orm_obj.is_ege_task,
            children=[CategoryDTO.from_orm_obj(child) for child in orm_obj.children],
        )
