import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from db_manager import DBManager
from fastapi.testclient import TestClient
from reply_server import app, get_current_user, _publish_product_to_account, _sync_items_after_publish


class PublishVisibilityTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db = DBManager(self.db_path)
        self.current_user = {"user_id": 7, "username": "operator", "is_admin": False}
        self.db.save_cookie("owned_account", "sid=owned; token=abc", user_id=7)

    def tearDown(self):
        app.dependency_overrides.pop(get_current_user, None)
        self.db.close()
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def test_publish_product_persists_minimal_item_when_sync_does_not_confirm_it(self):
        class FakeItemPublisher:
            def __init__(self, cookies_str, account_id):
                self.cookies_str = cookies_str
                self.account_id = account_id

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def publish_item(self, **kwargs):
                return {"ret": ["SUCCESS::OK"], "data": {"itemId": "published_123"}}

            def extract_published_item_id(self, publish_result):
                return "published_123"

            def is_success_response(self, publish_result):
                return True

            def extract_error_message(self, publish_result):
                return "unexpected failure"

        async def fake_sync_items_after_publish(cookie_id, cookies_str, published_item_id=None):
            return {
                "success": False,
                "message": "sync did not confirm item",
                "published_item_id": published_item_id,
                "item_synced": False,
                "page_sync": {"success": True, "current_count": 0, "saved_count": 0},
                "full_sync": {"used": False, "success": False, "total_count": 0, "total_saved": 0},
            }

        with patch("reply_server.db_manager", self.db), patch(
            "utils.item_publisher.ItemPublisher", FakeItemPublisher
        ), patch("reply_server._sync_items_after_publish", fake_sync_items_after_publish):
            result = asyncio.run(
                _publish_product_to_account(
                    current_user=self.current_user,
                    account_id="owned_account",
                    title="Visible after publish",
                    description="The item should appear before detail sync finishes",
                    images=[{"image_url": "/static/uploads/images/demo.jpg"}],
                    current_price=19.9,
                    original_price=None,
                    delivery_choice="包邮",
                    post_price=None,
                    can_self_pickup=False,
                )
            )

        saved = self.db.get_item_info("owned_account", "published_123")
        account_items = self.db.get_items_by_cookie("owned_account")

        self.assertTrue(result["success"])
        self.assertIsNotNone(saved)
        self.assertEqual(saved["item_title"], "Visible after publish")
        self.assertEqual(saved["item_price"], "19.9")
        self.assertIn("published_123", [item["item_id"] for item in account_items])

    def test_sync_with_published_item_requires_local_item_confirmation(self):
        class FakeXianyuLive:
            def __init__(self, cookies_str, account_id, register_instance=False):
                self.cookies_str = cookies_str
                self.account_id = account_id
                self.register_instance = register_instance

            async def get_item_list_info(self, page_number=1, page_size=100, sync_item_details=True):
                return {"success": True, "current_count": 1, "saved_count": 1, "items": [{"id": "other_item"}]}

            async def get_all_items(self, page_size=100, max_pages=3, sync_item_details=True):
                return {"success": True, "total_count": 1, "total_saved": 1, "items": [{"id": "other_item"}]}

            async def close_session(self):
                pass

        with patch("reply_server.db_manager", self.db), patch("XianyuAutoAsync.XianyuLive", FakeXianyuLive):
            result = asyncio.run(_sync_items_after_publish("owned_account", "sid=owned", "published_123"))

        self.assertFalse(result["success"])
        self.assertFalse(result["item_synced"])
        self.assertIn("published_123", result["message"])

    def test_publish_product_keeps_item_id_when_sync_updates_full_detail(self):
        class FakeItemPublisher:
            def __init__(self, cookies_str, account_id):
                self.cookies_str = cookies_str
                self.account_id = account_id

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def publish_item(self, **kwargs):
                return {"ret": ["SUCCESS::OK"], "data": {"itemId": "published_full"}}

            def extract_published_item_id(self, publish_result):
                return "published_full"

            def is_success_response(self, publish_result):
                return True

            def extract_error_message(self, publish_result):
                return "unexpected failure"

        async def fake_sync_items_after_publish(cookie_id, cookies_str, published_item_id=None):
            self.db.update_item_detail(
                cookie_id,
                published_item_id,
                json.dumps({"detail": "complete synced detail"}, ensure_ascii=False),
            )
            return {
                "success": True,
                "message": f"已同步发布商品 {published_item_id}",
                "published_item_id": published_item_id,
                "item_synced": True,
                "page_sync": {"success": True, "current_count": 1, "saved_count": 1},
                "full_sync": {"used": False, "success": False, "total_count": 0, "total_saved": 0},
            }

        with patch("reply_server.db_manager", self.db), patch(
            "utils.item_publisher.ItemPublisher", FakeItemPublisher
        ), patch("reply_server._sync_items_after_publish", fake_sync_items_after_publish):
            result = asyncio.run(
                _publish_product_to_account(
                    current_user=self.current_user,
                    account_id="owned_account",
                    title="Full sync title",
                    description="Initial publish description",
                    images=[{"image_url": "/static/uploads/images/demo.jpg"}],
                    current_price=29.9,
                    original_price=None,
                    delivery_choice="包邮",
                    post_price=None,
                    can_self_pickup=False,
                )
            )

        saved = self.db.get_item_info("owned_account", "published_full")

        self.assertTrue(result["success"])
        self.assertIsNotNone(saved)
        self.assertEqual(saved["item_id"], "published_full")
        self.assertEqual(saved["item_detail_parsed"]["detail"], "complete synced detail")

    def test_items_endpoints_return_published_item_for_owner(self):
        self.db.save_item_basic_info(
            "owned_account",
            "published_endpoint",
            item_title="Endpoint visible item",
            item_price="39.9",
        )

        app.dependency_overrides[get_current_user] = lambda: self.current_user

        with patch("db_manager.db_manager", self.db), patch("reply_server.db_manager", self.db):
            client = TestClient(app)
            all_items_response = client.get("/items")
            account_items_response = client.get("/items/cookie/owned_account")

        self.assertEqual(all_items_response.status_code, 200)
        self.assertEqual(account_items_response.status_code, 200)
        self.assertIn(
            "published_endpoint",
            [item["item_id"] for item in all_items_response.json()["items"]],
        )
        self.assertIn(
            "published_endpoint",
            [item["item_id"] for item in account_items_response.json()["items"]],
        )


if __name__ == "__main__":
    unittest.main()
