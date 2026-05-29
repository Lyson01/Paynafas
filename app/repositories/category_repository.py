from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, CategoryType


class CategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_slug(self, slug: str, user_id: int | None = None) -> Category | None:
        result = await self.session.execute(
            select(Category).where(
                Category.slug == slug,
                or_(Category.user_id == user_id, Category.user_id.is_(None)),
            )
        )
        return result.scalars().first()

    async def list_for_type(
        self, category_type: CategoryType | str, user_id: int | None = None
    ) -> list[Category]:
        value = category_type.value if isinstance(category_type, CategoryType) else category_type
        result = await self.session.execute(
            select(Category)
            .where(
                or_(Category.type == value, Category.type == CategoryType.BOTH),
                or_(Category.user_id == user_id, Category.user_id.is_(None)),
            )
            .order_by(Category.is_default.desc(), Category.name.asc())
        )
        return list(result.scalars())
