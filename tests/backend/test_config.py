from __future__ import annotations

import os
import unittest

from backend.app.config import Settings, get_settings


class SettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()

    def tearDown(self) -> None:
        get_settings.cache_clear()
        for key in list(os.environ):
            if key.startswith("VOLLEYBALL_AI_"):
                del os.environ[key]

    def test_default_settings(self) -> None:
        settings = Settings()
        self.assertEqual(settings.app_name, "Volleyball AI")
        self.assertEqual(settings.default_ruleset_variant, "6-player")

    def test_env_override(self) -> None:
        os.environ["VOLLEYBALL_AI_APP_NAME"] = "Custom Volleyball AI"
        os.environ["VOLLEYBALL_AI_DEBUG"] = "true"
        settings = get_settings()
        self.assertEqual(settings.app_name, "Custom Volleyball AI")
        self.assertTrue(settings.debug)


if __name__ == "__main__":
    unittest.main()

