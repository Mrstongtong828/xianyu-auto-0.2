from pathlib import Path
import re
import unittest


APP_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "app.js"


def read_app_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


def extract_function(source: str, function_name: str) -> str:
    match = re.search(rf"function\s+{re.escape(function_name)}\s*\([^)]*\)\s*{{", source)
    if not match:
        match = re.search(rf"async\s+function\s+{re.escape(function_name)}\s*\([^)]*\)\s*{{", source)
    if not match:
        raise AssertionError(f"{function_name} not found")

    index = match.end()
    depth = 1
    while index < len(source) and depth:
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    return source[match.start():index]


class StaticJsRequestHelperTests(unittest.TestCase):
    def test_dashboard_fetches_use_shared_authenticated_helper(self):
        source = read_app_js()

        self.assertIn("async function authenticatedFetch", source)
        fetch_dashboard_resource = extract_function(source, "fetchDashboardResource")
        load_dashboard = extract_function(source, "loadDashboard")
        load_items_count = extract_function(source, "loadItemsCount")
        load_order_metrics = extract_function(source, "loadOrderDashboardMetrics")
        load_sales_summary = extract_function(source, "loadSalesSummary")

        checked_blocks = [
            fetch_dashboard_resource,
            load_dashboard,
            load_items_count,
            load_order_metrics,
            load_sales_summary,
        ]
        for block in checked_blocks:
            self.assertNotIn("'Authorization': `Bearer", block)
            self.assertNotIn('"Authorization": `Bearer', block)

        self.assertIn("authenticatedFetch", fetch_dashboard_resource)
        self.assertIn("fetchJSON", load_dashboard)
        self.assertIn("fetchJSON", load_items_count)
        self.assertIn("fetchJSON", load_order_metrics)
        self.assertIn("fetchJSON", load_sales_summary)

    def test_dynamic_inner_html_injection_points_escape_api_data(self):
        source = read_app_js()

        render_notification_channels = extract_function(source, "renderNotificationChannels")
        test_ai_reply = extract_function(source, "testAIReply")
        show_version_info = extract_function(source, "showVersionInfo")

        self.assertIn("${escapeHtml(channel.id)}", render_notification_channels)
        self.assertIn("${escapeHtml(channel.name)}", render_notification_channels)
        self.assertIn("${escapeHtml(typeDisplay)}", render_notification_channels)
        self.assertIn("${configDisplay}", render_notification_channels)
        self.assertIn("escapeHtml(key)", render_notification_channels)
        self.assertIn("escapeHtml(displayValue)", render_notification_channels)
        self.assertIn("escapeHtml(channel.config", render_notification_channels)
        self.assertNotIn("${channel.name}", render_notification_channels)
        self.assertNotIn("${typeDisplay}", render_notification_channels)

        self.assertIn("escapeHtml(result.reply", test_ai_reply)
        self.assertNotIn("testReplyContent.innerHTML = result.reply", test_ai_reply)
        self.assertIn("escapeHtml(error.message", test_ai_reply)

        self.assertIn("escapeHtml(item.version", show_version_info)
        self.assertIn("escapeHtml(item.date", show_version_info)
        self.assertIn("escapeHtml(u)", show_version_info)
        self.assertIn("escapeHtml(intro)", show_version_info)

    def test_high_risk_frontend_requests_use_helper_and_confirmation_payload(self):
        source = read_app_js()

        clear_table_data = extract_function(source, "clearTableData")
        apply_hot_update = extract_function(source, "performHotUpdate")
        restart_application = extract_function(source, "restartApplication")
        do_restart_system = extract_function(source, "doRestartSystem")

        checked_blocks = [
            clear_table_data,
            apply_hot_update,
            restart_application,
            do_restart_system,
        ]
        for block in checked_blocks:
            self.assertIn("authenticatedFetch", block)
            self.assertIn("confirm_action", block)
            self.assertNotIn("'Authorization': `Bearer", block)
            self.assertNotIn('"Authorization": `Bearer', block)

    def test_fetch_json_clears_loading_state_on_success_and_failure(self):
        source = read_app_js()

        fetch_json = extract_function(source, "fetchJSON")

        self.assertIn("finally", fetch_json)
        self.assertRegex(fetch_json, r"finally\s*{\s*toggleLoading\(false\);")

    def test_dashboard_issue_center_tolerates_invalid_session_storage(self):
        source = read_app_js()

        get_ignored_keys = extract_function(source, "getDashboardIssueCenterIgnoredKeys")
        render_issue_center = extract_function(source, "renderDashboardIssueCenter")
        ignore_issue_once = extract_function(source, "ignoreDashboardIssueOnce")

        self.assertIn("try", get_ignored_keys)
        self.assertIn("catch", get_ignored_keys)
        self.assertIn("sessionStorage.getItem('dashboardIssueCenterIgnored')", get_ignored_keys)
        self.assertIn("getDashboardIssueCenterIgnoredKeys()", render_issue_center)
        self.assertIn("getDashboardIssueCenterIgnoredKeys()", ignore_issue_once)
        self.assertIn("bindDashboardIssueCenterActions()", render_issue_center)
        self.assertNotIn("onclick=\"handleDashboardIssueAction", render_issue_center)
        self.assertNotIn("onclick=\"ignoreDashboardIssueOnce", render_issue_center)
        self.assertNotIn("JSON.parse(sessionStorage.getItem('dashboardIssueCenterIgnored')", render_issue_center)
        self.assertNotIn("JSON.parse(sessionStorage.getItem('dashboardIssueCenterIgnored')", ignore_issue_once)


if __name__ == "__main__":
    unittest.main()
