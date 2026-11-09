import unittest

from tools.anime_release_monitor import (
    parse_feed,
    parse_episode,
    parse_release_hints,
    validate_sources,
    stable_release_id,
)


class ReleaseMonitorTests(unittest.TestCase):
    def test_rss_extracts_episode_quality_and_english_subtitle_metadata(self):
        xml = b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Creator Releases</title><item><title>Example Anime - Episode 07 [English Sub] [360p]</title><link>https://creator.example/releases/ep-7</link><guid>release-7</guid><pubDate>Sun, 08 Nov 2026 12:00:00 GMT</pubDate><description>Official creator release.</description></item></channel></rss>'''
        releases = parse_feed(xml, {"id": "creator", "name": "Creator", "rights_status": "metadata_only"})
        self.assertEqual(len(releases), 1)
        release = releases[0]
        self.assertEqual(release["episode"], "7")
        self.assertIn(360, release["resolutions"])
        self.assertEqual(release["subtitle_languages"], ["English"])
        self.assertEqual(release["source_url"], "https://creator.example/releases/ep-7")
        self.assertNotIn("media_url", release)

    def test_atom_feed_extracts_link_and_episode(self):
        xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Studio</title><entry><title>Moon Story S02E03 720p</title><id>tag:studio.example,2026:ep3</id><link rel="alternate" href="https://studio.example/episodes/3"/><updated>2026-11-08T12:30:00Z</updated></entry></feed>'''
        releases = parse_feed(xml, {"id": "studio", "name": "Studio", "rights_status": "metadata_only"})
        self.assertEqual(releases[0]["episode"], "S02E03")
        self.assertIn(720, releases[0]["resolutions"])
        self.assertEqual(releases[0]["source_url"], "https://studio.example/episodes/3")

    def test_episode_parser_handles_common_patterns(self):
        self.assertEqual(parse_episode("Show - Episode 12"), "12")
        self.assertEqual(parse_episode("Show S01E09 1080p"), "S01E09")
        self.assertIsNone(parse_episode("Show movie edition"))

    def test_release_hints_do_not_infer_missing_metadata(self):
        self.assertEqual(parse_release_hints("Show episode 2"), {"resolutions": [], "subtitle_languages": []})

    def test_authorized_source_requires_license_evidence(self):
        with self.assertRaises(ValueError):
            validate_sources({"schema_version": 1, "sources": [{"id": "x", "name": "X", "feed_url": "https://x.example/rss", "rights_status": "redistribution_authorized"}]})

    def test_source_requires_https_feed_url(self):
        with self.assertRaises(ValueError):
            validate_sources({"schema_version": 1, "sources": [{"id": "x", "name": "X", "feed_url": "http://x.example/rss", "rights_status": "metadata_only"}]})

    def test_stable_release_id_is_deterministic(self):
        a = stable_release_id("source", "guid-1", "Example episode 1")
        b = stable_release_id("source", "guid-1", "Example episode 1")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("rel-"))


if __name__ == "__main__":
    unittest.main()
