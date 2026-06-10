from pathlib import Path
import unittest


REPLY_SERVER = Path(__file__).resolve().parents[1] / "reply_server.py"
APP_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "app.js"
INDEX_HTML = Path(__file__).resolve().parents[1] / "static" / "index.html"


class AdminPendingActionsTests(unittest.TestCase):
    def test_reply_server_defines_pending_action_lifecycle(self):
        source = REPLY_SERVER.read_text(encoding="utf-8")

        self.assertIn("pending_admin_actions", source)
        self.assertIn("def create_pending_admin_action", source)
        self.assertIn("def confirm_pending_admin_action", source)
        self.assertIn("@app.get('/admin/pending-actions')", source)
        self.assertIn("@app.post('/admin/pending-actions/{action_id}/cancel')", source)
        self.assertIn("Depends(require_admin)", source)
        self.assertIn("admin_action.pending", source)
        self.assertIn("admin_action.confirmed", source)
        self.assertIn("admin_action.cancelled", source)
        self.assertIn("admin_action.expired", source)

    def test_pending_action_is_not_consumed_before_type_and_target_match(self):
        source = REPLY_SERVER.read_text(encoding="utf-8")

        self.assertIn("expected_action: str = ''", source)
        self.assertIn("expected_target_id: str = ''", source)
        confirm_index = source.index("def confirm_pending_admin_action")
        action_match_index = source.index("if expected_action and action.get('action') != expected_action:", confirm_index)
        target_match_index = source.index("if expected_target_id and str(action.get('target_id') or '') != str(expected_target_id or ''):", confirm_index)
        pop_index = source.index("pending_admin_actions.pop(normalized_id, None)", target_match_index)

        self.assertLess(action_match_index, pop_index)
        self.assertLess(target_match_index, pop_index)

    def test_frontend_renders_issue_center_and_pending_action_confirmation(self):
        app_js = APP_JS.read_text(encoding="utf-8")
        index_html = INDEX_HTML.read_text(encoding="utf-8")

        self.assertIn("dashboardIssueCenter", index_html)
        self.assertIn("renderDashboardIssueCenter", app_js)
        self.assertIn("action_items", app_js)
        self.assertIn("createPendingAdminAction", app_js)
        self.assertIn("confirmPendingAdminAction", app_js)
        self.assertIn("cancelPendingAdminAction", app_js)
        self.assertIn("pending_action_id", app_js)
        self.assertIn("/admin/pending-actions", app_js)


if __name__ == "__main__":
    unittest.main()
