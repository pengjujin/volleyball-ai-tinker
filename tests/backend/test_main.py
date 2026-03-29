from __future__ import annotations

import unittest

from backend.app.api.health import health_check
from backend.app.api.info import get_app_info
from backend.app._compat import get_registered_routes
from backend.app.main import create_app


class MainAppTest(unittest.TestCase):
    def test_health_endpoint_payload(self) -> None:
        self.assertEqual(health_check(), {"status": "ok"})

    def test_info_endpoint_payload(self) -> None:
        payload = get_app_info()
        self.assertEqual(payload["name"], "Volleyball AI")
        self.assertEqual(payload["version"], "0.1.0")
        self.assertIn("environment", payload)
        self.assertIn("default_ruleset_variant", payload)

    def test_routes_registered(self) -> None:
        routes = get_registered_routes(create_app())
        route_signatures = {(route.path, tuple(route.methods)) for route in routes}
        self.assertIn(("/health", ("GET",)), route_signatures)
        self.assertIn(("/info", ("GET",)), route_signatures)
        self.assertIn(("/api/videos", ("POST",)), route_signatures)
        self.assertIn(("/api/videos/{video_asset_id}", ("GET",)), route_signatures)


if __name__ == "__main__":
    unittest.main()
