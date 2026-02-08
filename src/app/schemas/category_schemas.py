from pydantic import BaseModel

from app.enums import HandlerType
from app.models import Category


class CategoryDTO(BaseModel):
    id: int
    name: str
    handler_type: HandlerType | None
    parent_id: int | None

    @classmethod
    def from_orm_obj(cls, orm_obj: Category) -> "CategoryDTO":
        return cls(
            id=orm_obj.id,
            name=orm_obj.name,
            handler_type=orm_obj.handler_type,
            parent_id=orm_obj.parent_id,
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
            children=[CategoryDTO.from_orm_obj(child) for child in orm_obj.children],
        )
