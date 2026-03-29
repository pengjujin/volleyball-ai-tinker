from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
import unittest

from backend.app.schemas.common import RulesetVariant
from backend.app.services.local_analysis import run_local_analysis


class LocalAnalysisTest(unittest.TestCase):
    def test_run_local_analysis_creates_static_report_files(self) -> None:
        temp_video = NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_video.write(b"tiny-video")
        temp_video.flush()
        temp_video.close()

        try:
            with TemporaryDirectory() as temp_output_dir:
                result = run_local_analysis(
                    video_path=Path(temp_video.name),
                    ruleset_variant=RulesetVariant.six_player,
                    title="Short clip",
                    output_root=temp_output_dir,
                )

                self.assertTrue(result.report_path.exists())
                self.assertTrue(result.analysis_json_path.exists())
                self.assertTrue(result.report_url.startswith("file://"))
                self.assertGreaterEqual(len(result.set_events), 1)
                self.assertEqual(result.video_source_type.value, "local_path")

                report_html = result.report_path.read_text(encoding="utf-8")
                analysis_json = result.analysis_json_path.read_text(encoding="utf-8")

                self.assertIn("Short clip", report_html)
                self.assertIn("Volleyball AI Local Report", report_html)
                self.assertIn("Short clip", analysis_json)
                self.assertIn(result.video_asset_id, analysis_json)
        finally:
            video_path = Path(temp_video.name)
            if video_path.exists():
                video_path.unlink()

    def test_run_local_analysis_accepts_youtube_url(self) -> None:
        with TemporaryDirectory() as temp_output_dir:
            result = run_local_analysis(
                youtube_url="https://www.youtube.com/watch?v=abc123",
                ruleset_variant=RulesetVariant.nine_man,
                title="YouTube Clip",
                output_root=temp_output_dir,
            )

            self.assertTrue(result.report_path.exists())
            self.assertEqual(result.video_source_type.value, "youtube")
            self.assertIsNone(result.video_path)
            self.assertEqual(result.video_url, "https://www.youtube.com/watch?v=abc123")

            analysis_json = result.analysis_json_path.read_text(encoding="utf-8")
            self.assertIn('"video_source_type": "youtube"', analysis_json)
            self.assertIn("YouTube Clip", analysis_json)
