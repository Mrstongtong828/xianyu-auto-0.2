from pathlib import Path
import re
import unittest


REPLY_SERVER = Path(__file__).resolve().parents[1] / "reply_server.py"


def read_reply_server() -> str:
    return REPLY_SERVER.read_text(encoding="utf-8")


class ReplyServerHighRiskAuthTests(unittest.TestCase):
    def test_admin_routes_use_unified_admin_dependency(self):
        source = read_reply_server()
        admin_routes = [
            "@app.get('/admin/users')",
            "@app.delete('/admin/users/{user_id}')",
            "@app.put('/admin/users/{user_id}/admin-status')",
            "@app.get('/admin/data/{table_name}')",
            "@app.get('/admin/data/{table_name}/export')",
            "@app.delete('/admin/data/{table_name}/{record_id}')",
            "@app.delete('/admin/data/{table_name}')",
        ]

        for route in admin_routes:
            route_index = source.index(route)
            next_route = source.find("\n@app.", route_index + 1)
            block = source[route_index: next_route if next_route != -1 else len(source)]
            self.assertIn("Depends(require_admin)", block, route)

    def test_update_routes_use_unified_admin_check(self):
        source = read_reply_server()
        update_routes = [
            "@app.post('/api/update/apply')",
            "@app.post('/api/update/restart')",
        ]

        for route in update_routes:
            route_index = source.index(route)
            next_route = source.find("\n@app.", route_index + 1)
            block = source[route_index: next_route if next_route != -1 else len(source)]
            self.assertIn("Depends(require_admin)", block, route)
            self.assertIn("require_admin_confirmation", block, route)
            self.assertNotRegex(block, re.compile(r"username['\"]?\s*==\s*['\"]admin['\"]"))

    def test_destructive_admin_routes_require_explicit_confirmation(self):
        source = read_reply_server()
        destructive_routes = [
            "@app.delete('/admin/data/{table_name}')",
            "@app.post('/api/update/apply')",
            "@app.post('/api/update/restart')",
        ]

        self.assertIn("def require_admin_confirmation", source)
        for route in destructive_routes:
            route_index = source.index(route)
            next_route = source.find("\n@app.", route_index + 1)
            block = source[route_index: next_route if next_route != -1 else len(source)]
            self.assertIn("confirm_action", block, route)
            self.assertIn("require_admin_confirmation", block, route)

    def test_session_tokens_do_not_use_static_jwt_secret_fallback(self):
        source = read_reply_server()

        self.assertIn("def generate_token", source)
        self.assertIn("secrets.token_urlsafe(32)", source)
        self.assertNotIn("JWT_SECRET_KEY = ", source)
        self.assertNotIn("jwt.encode", source)
        self.assertNotIn("jwt.decode", source)

    def test_client_ip_trusts_forwarded_headers_only_from_trusted_proxies(self):
        source = read_reply_server()

        self.assertIn("TRUSTED_PROXY_CIDRS", source)
        self.assertIn("def _is_trusted_proxy_ip", source)
        self.assertIn("def _get_first_valid_forwarded_ip", source)
        self.assertIn("if _is_trusted_proxy_ip(direct_ip):", source)

        sensitive_routes = [
            "@app.get('/captcha/generate')",
            "@app.get('/captcha/check-required')",
            "@app.post('/login')",
        ]
        for route in sensitive_routes:
            route_index = source.index(route)
            next_route = source.find("\n@app.", route_index + 1)
            block = source[route_index: next_route if next_route != -1 else len(source)]
            self.assertIn("get_request_client_ip(request)", block, route)
            self.assertNotIn("request.headers.get('X-Forwarded-For'", block, route)
            self.assertNotIn("request.headers.get('X-Real-IP'", block, route)


if __name__ == "__main__":
    unittest.main()
