from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentSecurityTests(unittest.TestCase):
    def test_compose_files_do_not_default_to_weak_admin_secrets(self):
        for filename in ("docker-compose.yml", "docker-compose-cn.yml"):
            source = (ROOT / filename).read_text(encoding="utf-8")
            self.assertNotIn("ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}", source)
            self.assertNotIn("JWT_SECRET_KEY=${JWT_SECRET_KEY:-default-secret-key}", source)
            self.assertIn("ADMIN_PASSWORD=${ADMIN_PASSWORD:?set ADMIN_PASSWORD", source)
            self.assertIn("JWT_SECRET_KEY=${JWT_SECRET_KEY:?set JWT_SECRET_KEY", source)

    def test_nginx_csp_is_script_specific_and_documents_inline_exception(self):
        source = (ROOT / "nginx" / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("script-src 'self' 'unsafe-inline'", source)
        self.assertNotIn("default-src 'self' http: https: data: blob: 'unsafe-inline'", source)

    def test_app_and_vnc_ports_bind_to_localhost_by_default(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        compose_cn = (ROOT / "docker-compose-cn.yml").read_text(encoding="utf-8")

        self.assertIn('"127.0.0.1:9000:8090"', compose)
        self.assertIn('"127.0.0.1:5900:5900"', compose)
        self.assertNotIn('"9000:8090"', compose)
        self.assertNotIn('"5900:5900"', compose)

        self.assertIn('"127.0.0.1:8000:8090"', compose_cn)
        self.assertNotIn('"8000:8090"', compose_cn)


if __name__ == "__main__":
    unittest.main()
