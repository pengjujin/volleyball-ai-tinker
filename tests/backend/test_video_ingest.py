from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
import unittest
from time import sleep

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.schemas.common import ProcessingStage, RulesetVariant, VideoSourceType
from backend.app.services.video_registry import get_video_registry


class VideoRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = get_video_registry()
        self.registry.reset()
        temp_file = NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_file.write(b"test-video")
        temp_file.flush()
        temp_file.close()
        self.local_video_path = Path(temp_file.name)

    def tearDown(self) -> None:
        self.registry.reset()
        if self.local_video_path.exists():
            self.local_video_path.unlink()

    def test_create_upload_video_summary(self) -> None:
        summary = self.registry.create_video(
            title="",
            source_type=VideoSourceType.upload,
            ruleset_variant=RulesetVariant.six_player,
            source_file_name="match-one.mp4",
            source_file_bytes=b"fake-video",
            source_mime_type="video/mp4",
        )

        self.assertEqual(summary.status, ProcessingStage.queued)
        self.assertEqual(summary.progress, 0.0)
        self.assertEqual(summary.source_type, VideoSourceType.upload)
        self.assertEqual(summary.ruleset_variant, RulesetVariant.six_player)
        self.assertEqual(summary.source_file_name, "match-one.mp4")
        self.assertEqual(summary.mime_type, "video/mp4")
        self.assertTrue(summary.local_path is not None)
        self.assertTrue(summary.normalized_asset.path.endswith("/normalized.mp4"))
        self.assertTrue(summary.proxy_asset.path.endswith("/proxy.mp4"))

    def test_create_youtube_video_requires_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "sourceUrl is required"):
            self.registry.create_video(
                title="Sample",
                source_type=VideoSourceType.youtube,
                ruleset_variant=RulesetVariant.nine_man,
            )

    def test_create_local_path_video_uses_existing_file_without_copy(self) -> None:
        summary = self.registry.create_video(
            title="",
            source_type=VideoSourceType.local_path,
            ruleset_variant=RulesetVariant.six_player,
            local_path=str(self.local_video_path),
        )

        self.assertEqual(summary.source_type, VideoSourceType.local_path)
        self.assertEqual(summary.local_path, str(self.local_video_path.resolve()))
        self.assertIsNone(summary.source_file_name)
        self.assertEqual(summary.status, ProcessingStage.queued)

    def test_background_processing_stores_events_and_analytics(self) -> None:
        summary = self.registry.create_video(
            title="Clip",
            source_type=VideoSourceType.local_path,
            ruleset_variant=RulesetVariant.six_player,
            local_path=str(self.local_video_path),
        )

        self.registry.start_processing(summary.id)

        for _ in range(50):
            refreshed = self.registry.get_video(summary.id)
            if refreshed is not None and refreshed.status == ProcessingStage.completed:
                break
            sleep(0.02)

        refreshed = self.registry.get_video(summary.id)
        self.assertIsNotNone(refreshed)
        assert refreshed is not None
        self.assertEqual(refreshed.status, ProcessingStage.completed)
        events = self.registry.get_events(summary.id)
        analytics = self.registry.get_analytics(summary.id)
        self.assertIsNotNone(events)
        self.assertIsNotNone(analytics)
        assert events is not None
        assert analytics is not None
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(analytics.video_asset_id, summary.id)


class VideoEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = get_video_registry()
        self.registry.reset()
        self.client = TestClient(create_app())
        temp_file = NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_file.write(b"test-video")
        temp_file.flush()
        temp_file.close()
        self.local_video_path = Path(temp_file.name)

    def tearDown(self) -> None:
        self.registry.reset()
        if self.local_video_path.exists():
            self.local_video_path.unlink()

    def test_post_upload_video_returns_summary(self) -> None:
        response = self.client.post(
            "/api/videos",
            data={
                "title": "Friday night match",
                "sourceType": "upload",
                "rulesetVariant": "6-player",
            },
            files={"file": ("match.mp4", b"fake-video-bytes", "video/mp4")},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["status"], "queued")
        self.assertEqual(payload["progress"], 0.0)
        self.assertEqual(payload["sourceType"], "upload")
        self.assertEqual(payload["rulesetVariant"], "6-player")
        self.assertEqual(payload["sourceFileName"], "match.mp4")
        self.assertIn("normalizedAsset", payload)
        self.assertIn("proxyAsset", payload)

        video_id = payload["id"]
        detail = self.client.get(f"/api/videos/{video_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["id"], video_id)

    def test_post_youtube_video_returns_summary(self) -> None:
        response = self.client.post(
            "/api/videos",
            data={
                "title": "Tournament semifinal",
                "sourceType": "youtube",
                "sourceUrl": "https://www.youtube.com/watch?v=abc123",
                "rulesetVariant": "9-man",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["sourceType"], "youtube")
        self.assertEqual(payload["sourceUrl"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(payload["rulesetVariant"], "9-man")
        self.assertIsNone(payload["sourceFileName"])

    def test_post_local_path_video_returns_summary(self) -> None:
        response = self.client.post(
            "/api/videos",
            data={
                "title": "Local path match",
                "sourceType": "local_path",
                "localPath": str(self.local_video_path),
                "rulesetVariant": "6-player",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["sourceType"], "local_path")
        self.assertEqual(payload["localPath"], str(self.local_video_path.resolve()))
        self.assertEqual(payload["rulesetVariant"], "6-player")
        self.assertIsNone(payload["sourceFileName"])

    def test_get_missing_video_returns_404(self) -> None:
        response = self.client.get("/api/videos/video-does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_processed_video_exposes_events_and_analytics(self) -> None:
        response = self.client.post(
            "/api/videos",
            data={
                "title": "Small clip",
                "sourceType": "upload",
                "rulesetVariant": "6-player",
            },
            files={"file": ("clip.mp4", b"small-video", "video/mp4")},
        )

        self.assertEqual(response.status_code, 201)
        video_id = response.json()["id"]

        for _ in range(50):
            detail = self.client.get(f"/api/videos/{video_id}")
            if detail.status_code == 200 and detail.json()["status"] == "completed":
                break
            sleep(0.02)

        events = self.client.get(f"/api/videos/{video_id}/events")
        analytics = self.client.get(f"/api/videos/{video_id}/analytics")

        self.assertEqual(events.status_code, 200)
        self.assertEqual(analytics.status_code, 200)
        self.assertGreaterEqual(len(events.json()), 1)
        self.assertEqual(analytics.json()["video_asset_id"], video_id)


if __name__ == "__main__":
    unittest.main()
