from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer"
LAUNCHER = INSTALLER / "Start-XianyuDocker.ps1"
COMMON = INSTALLER / "XianyuDocker.Common.ps1"


def read_installer_sources():
    return "\n".join(path.read_text(encoding="utf-8") for path in INSTALLER.glob("*.ps1"))


class WindowsDockerLauncherTests(unittest.TestCase):
    def test_launcher_contains_required_operational_steps(self):
        source = read_installer_sources()

        self.assertIn("docker compose version", source)
        self.assertIn("docker info", source)
        self.assertIn("docker-compose-cn.yml", source)
        self.assertIn('"-f"', source)
        self.assertIn("/health", source)
        self.assertIn("Start-Process", source)

    def test_launcher_creates_persistent_directories(self):
        source = read_installer_sources()

        for directory in (
            "data",
            "logs",
            "backups",
            "static",
            "static/uploads",
            "static/uploads/images",
        ):
            self.assertIn(directory, source)

    def test_launcher_generates_required_env_without_hardcoded_secrets(self):
        source = read_installer_sources()

        self.assertIn('"ADMIN_USERNAME"', source)
        self.assertIn('"admin"', source)
        self.assertIn("ADMIN_PASSWORD", source)
        self.assertIn("JWT_SECRET_KEY", source)
        self.assertIn("SECRET_ENCRYPTION_KEY", source)
        self.assertIn("RandomNumberGenerator", source)
        self.assertIn("Read-XianyuAdminPassword", source)
        self.assertIn("Read-Host", source)
        self.assertNotIn("admin123", source)
        self.assertNotIn("default-secret-key", source)

    def test_launcher_has_non_destructive_env_update_path(self):
        source = read_installer_sources()

        self.assertIn("Read-EnvFile", source)
        self.assertIn("Set-EnvValue", source)
        self.assertIn("Test-Path", source)
        self.assertIn("UTF8Encoding", source)
        self.assertNotIn("Remove-Item .env", source)

    def test_docker_desktop_install_is_explicit(self):
        source = (INSTALLER / "Install-XianyuDocker.ps1").read_text(encoding="utf-8")

        self.assertIn("[switch]$InstallDockerDesktop", source)
        self.assertIn("-InstallDockerDesktop:$InstallDockerDesktop", source)
        self.assertNotIn("(!$SkipDockerDesktopInstall)", source)

    def test_command_wrappers_are_present_for_exe_packaging(self):
        for name in ("install.cmd", "start.cmd", "status.cmd", "logs.cmd", "stop.cmd", "open.cmd", "uninstall.cmd"):
            self.assertTrue((INSTALLER / name).exists(), name)

    def test_entry_scripts_expose_help_and_dry_run(self):
        for path in INSTALLER.glob("*-XianyuDocker.ps1"):
            source = path.read_text(encoding="utf-8")
            self.assertIn("[switch]$Help", source, path.name)
            self.assertIn("[switch]$DryRun", source, path.name)
            self.assertIn("Show-XianyuLauncherHelp", source, path.name)
            self.assertIn("Write-XianyuDryRun", source, path.name)

    def test_command_wrappers_use_non_profile_bypass_mode(self):
        for path in INSTALLER.glob("*.cmd"):
            source = path.read_text(encoding="utf-8")
            self.assertIn("chcp 65001", source, path.name)
            self.assertIn("-NoProfile", source, path.name)
            self.assertIn("-ExecutionPolicy Bypass", source, path.name)


if __name__ == "__main__":
    unittest.main()
