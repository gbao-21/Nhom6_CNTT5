"""Kiểm thử các API thực đơn dành cho khách hàng."""
import unittest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.dependencies import get_db
from app.main import app
from app.models.category import Category
from app.models.dish import Dish, DishOption


class MenuApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            autoflush=False,
            bind=cls.engine,
        )

    def setUp(self):
        Base.metadata.create_all(bind=self.engine)
        self.db = self.TestingSessionLocal()

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        active_category = Category(id=1, name="Món chính", is_active=True)
        hidden_category = Category(id=2, name="Danh mục ẩn", is_active=False)
        self.db.add_all([active_category, hidden_category])
        self.db.flush()
        self.db.add_all(
            [
                Dish(
                    id=1,
                    category_id=1,
                    name="Mì trộn",
                    price=Decimal("45000"),
                    is_available=True,
                    is_active=True,
                    status="AVAILABLE",
                ),
                Dish(
                    id=2,
                    category_id=1,
                    name="Cơm gà hết hàng",
                    price=Decimal("55000"),
                    is_available=True,
                    is_active=True,
                    status="OUT_OF_STOCK",
                ),
                Dish(
                    id=3,
                    category_id=1,
                    name="Món đã ẩn",
                    price=Decimal("35000"),
                    is_active=False,
                    status="HIDDEN",
                ),
                Dish(
                    id=4,
                    category_id=2,
                    name="Thuộc danh mục ẩn",
                    price=Decimal("25000"),
                ),
            ]
        )
        self.db.flush()
        self.db.add(
            DishOption(
                dish_id=1,
                name="Thêm trứng",
                price=Decimal("5000"),
                is_available=True,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.client.close()
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        app.dependency_overrides.clear()

    def test_overview_and_root_alias_return_visible_menu(self):
        for path in ("/api/menu", "/api/menu/overview"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            categories = response.json()["categories"]
            self.assertEqual([category["name"] for category in categories], ["Món chính"])
            self.assertEqual(
                [dish["name"] for dish in categories[0]["dishes"]],
                ["Mì trộn", "Cơm gà hết hàng"],
            )

    def test_dish_list_aliases_support_search_and_category_filter(self):
        for path in ("/api/menu/items", "/api/menu/dishes"):
            response = self.client.get(
                path,
                params={"category_id": 1, "q": "Mì"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual([dish["name"] for dish in response.json()], ["Mì trộn"])

    def test_dish_detail_aliases_include_options_and_hide_unavailable_entries(self):
        for path in ("/api/menu/items/1", "/api/menu/dishes/1"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["options"][0]["name"], "Thêm trứng")

        for hidden_id in (3, 4, 999):
            response = self.client.get(f"/api/menu/dishes/{hidden_id}")
            self.assertEqual(response.status_code, 404)

    def test_active_categories_only(self):
        response = self.client.get("/api/menu/categories")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [category["name"] for category in response.json()],
            ["Món chính"],
        )


if __name__ == "__main__":
    unittest.main()
