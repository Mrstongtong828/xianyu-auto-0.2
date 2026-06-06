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


if __name__ == "__main__":
    unittest.main()
