import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.anime_media_pipeline import process_manifest


class AnimeMediaPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.incoming = self.root / "incoming"
        self.output = self.root / "encoded"
        self.incoming.mkdir()
        (self.incoming / "episode.mp4").write_bytes(b"authorised input")
        (self.incoming / "episode.en.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n", encoding="utf-8")
        self.manifest = self.root / "manifest.json"
        self.document = {
            "schema_version": 1,
            "assets": [{
                "id": "space-mercenary-episode-01",
                "title": "Space Mercenary Episode 1",
                "input_file": "episode.mp4",
                "rights_status": "redistribution_authorized",
                "license": "Written creator licence",
                "rights_evidence_url": "https://creator.example/license",
                "subtitle_file": "episode.en.srt",
                "subtitle_language": "English"
            }]
        }
        self.write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.document), encoding="utf-8")

    def fake_ffmpeg(self, command, **kwargs):
        Path(command[-1]).write_bytes(b"encoded mp4")
        return type("Completed", (), {"returncode": 0})()

    def test_authorized_input_generates_360p_first_profiles_and_english_subtitle(self):
        with patch("tools.anime_media_pipeline.subprocess.run", side_effect=self.fake_ffmpeg) as runner:
            result = process_manifest(self.manifest, self.incoming, self.output)
        self.assertEqual(result["asset_count"], 1)
        self.assertEqual(result["assets"][0]["profiles"], [360, 480, 720, 1080])
        self.assertTrue((self.output / "space-mercenary-episode-01" / "360p.mp4").is_file())
        self.assertTrue((self.output / "space-mercenary-episode-01" / "english.srt").is_file())
        self.assertEqual(runner.call_count, 4)
        self.assertIn("scale=-2:min(ih\\,360)", runner.call_args_list[0].args[0])

    def test_rejects_assets_without_explicit_redistribution_rights(self):
        self.document["assets"][0]["rights_status"] = "metadata_only"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "redistribution_authorized"):
            process_manifest(self.manifest, self.incoming, self.output)

    def test_rejects_missing_english_subtitle_when_declared_required(self):
        self.document["assets"][0]["subtitle_file"] = "missing.srt"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "subtitle"):
            process_manifest(self.manifest, self.incoming, self.output)

    def test_rejects_path_traversal_outside_incoming_directory(self):
        self.document["assets"][0]["input_file"] = "../outside.mp4"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "inside"):
            process_manifest(self.manifest, self.incoming, self.output)

    def test_failed_ffmpeg_does_not_publish_partial_asset_directory(self):
        with patch("tools.anime_media_pipeline.subprocess.run", side_effect=RuntimeError("ffmpeg failed")):
            with self.assertRaisesRegex(RuntimeError, "ffmpeg failed"):
                process_manifest(self.manifest, self.incoming, self.output)
        self.assertFalse((self.output / "space-mercenary-episode-01").exists())


if __name__ == "__main__":
    unittest.main()
