from sqlalchemy.orm import Session
from src.models.category import Category


class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_category_tree(self) -> list:
        categories = self.db.query(Category).filter(
            Category.is_active == True
        ).all()

        cat_map = {}
        for cat in categories:
            cat_map[cat.id] = {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "parent_id": cat.parent_id,
                "children": []
            }

        roots = []
        for cat_id, cat_data in cat_map.items():
            parent_id = cat_data.get("parent_id")
            if parent_id and parent_id in cat_map:
                cat_map[parent_id]["children"].append(cat_data)
            else:
                roots.append(cat_data)

        return roots

    def get_category_by_id(self, category_id: str) -> dict | None:
        cat = self.db.query(Category).filter(
            Category.id == category_id,
            Category.is_active == True
        ).first()

        if not cat:
            return None

        return {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "parent_id": cat.parent_id,
            "description": cat.description,
            "is_active": cat.is_active
        }

    def get_categories_by_ids(self, ids: list[str]) -> dict:
        categories = self.db.query(Category).filter(
            Category.id.in_(ids),
            Category.is_active == True
        ).all()

        return {cat.id: cat.name for cat in categories}

    def seed_categories(self):
        """Create default categories if none exist"""
        if self.db.query(Category).count() > 0:
            return

        electronics = Category(
            id=str(uuid.uuid4()),
            name="Электроника",
            slug="electronics",
            parent_id=None
        )
        self.db.add(electronics)
        self.db.flush()

        smartphones = Category(
            id=str(uuid.uuid4()),
            name="Смартфоны",
            slug="smartphones",
            parent_id=electronics.id
        )
        self.db.add(smartphones)

        laptops = Category(
            id=str(uuid.uuid4()),
            name="Ноутбуки",
            slug="laptops",
            parent_id=electronics.id
        )
        self.db.add(laptops)

        clothes = Category(
            id=str(uuid.uuid4()),
            name="Одежда",
            slug="clothes",
            parent_id=None
        )
        self.db.add(clothes)

        self.db.commit()


import uuid
