"""Tests for customer-facing menu endpoints."""
import unittest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.category import Category
from app.models.dish import Dish


class MenuRoutesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.seed_data()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        app.dependency_overrides.clear()

    def seed_data(self):
        active_category = Category(id=1, name="Món chính", is_active=True)
        inactive_category = Category(id=2, name="Ẩn", is_active=False)
        self.db.add_all([active_category, inactive_category])
        self.db.add_all(
            [
                Dish(
                    id=1,
                    category_id=1,
                    name="Phở bò",
                    price=Decimal("50000"),
                    is_available=True,
                    is_active=True,
                ),
                Dish(
                    id=2,
                    category_id=1,
                    name="Bún bò",
                    price=Decimal("40000"),
                    is_available=False,
                    is_active=True,
                ),
                Dish(
                    id=3,
                    category_id=1,
                    name="Món ẩn",
                    price=Decimal("30000"),
                    is_available=True,
                    is_active=False,
                ),
                Dish(
                    id=4,
                    category_id=2,
                    name="Không hiển thị",
                    price=Decimal("20000"),
                    is_available=True,
                    is_active=True,
                ),
            ]
        )
        self.db.commit()

    def test_menu_dish_endpoint_filters_and_returns_paged_items(self):
        response = self.client.get(
            "/api/menu/dishes",
            params={
                "is_available": "true",
                "search": "phở",
                "category_id": 1,
                "min_price": 40000,
                "max_price": 60000,
                "page": 1,
                "page_size": 5,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["items"][0]["name"], "Phở bò")

    def test_menu_categories_and_overview_hide_inactive_records(self):
        categories_response = self.client.get("/api/menu/categories")
        overview_response = self.client.get("/api/menu/overview")

        self.assertEqual(categories_response.status_code, 200)
        self.assertEqual(
            [category["name"] for category in categories_response.json()],
            ["Món chính"],
        )
        self.assertEqual(overview_response.status_code, 200)
        overview_category = overview_response.json()["categories"][0]
        self.assertEqual(
            [dish["name"] for dish in overview_category["dishes"]],
            ["Phở bò", "Bún bò"],
        )


if __name__ == "__main__":
    unittest.main()
