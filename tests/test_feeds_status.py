import json
import tempfile
import unittest
from pathlib import Path
from urllib import error, request

from services.feeds_status_service import (
    build_event_display_link,
    build_summary_entry_id,
    build_summary_entry_link,
    build_summary_entry_datetime,
    build_summary_entry_title,
    get_failed_feeds,
    load_feeds_status_state,
    should_render_summary_entry,
    update_feeds_status_state,
)


def _read_miniflux_config(config_file):
    try:
        from yaml import safe_load

        config = safe_load(config_file.read_text(encoding="utf-8")) or {}
        miniflux_config = config.get("miniflux", {})
        return {
            "base_url": miniflux_config.get("base_url"),
            "api_key": miniflux_config.get("api_key"),
        }
    except ImportError:
        section_indent = None
        in_miniflux_section = False
        result = {"base_url": None, "api_key": None}

        for raw_line in config_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())
            if stripped == "miniflux:":
                in_miniflux_section = True
                section_indent = indent
                continue

            if in_miniflux_section and indent <= section_indent:
                break

            if in_miniflux_section and ":" in stripped:
                key, value = stripped.split(":", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in result:
                    result[key] = value

        return result


def _fetch_feeds_from_server(base_url, api_key):
    req = request.Request(
        base_url.rstrip("/") + "/v1/feeds",
        headers={
            "X-Auth-Token": api_key,
            "Accept": "application/json",
        },
    )
    with request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


class FeedsStatusTestCase(unittest.TestCase):
    def test_get_failed_feeds_filters_by_error_fields(self):
        feeds = [
            {
                "id": 81,
                "title": "Reuters World News",
                "feed_url": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
                "site_url": "https://www.reuters.com/world/",
                "disabled": False,
                "parsing_error_count": 3246,
                "parsing_error_message": "Failed to fetch feed because the upstream server denied access.",
                "checked_at": "2026-03-17T14:41:34.870212+08:00",
            },
            {
                "id": 82,
                "title": "Healthy Feed",
                "feed_url": "https://example.com/feed.xml",
                "site_url": "https://example.com/",
                "disabled": False,
                "parsing_error_count": 0,
                "parsing_error_message": "",
                "checked_at": "2026-03-17T14:41:34.870212+08:00",
            },
            {
                "id": 80,
                "title": "Disabled Broken Feed",
                "feed_url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
                "site_url": "https://www.nytimes.com/",
                "disabled": True,
                "parsing_error_count": 1,
                "parsing_error_message": "The feed is disabled and should be ignored by the collector.",
                "checked_at": "2024-12-06T19:48:29.839462+08:00",
            },
        ]

        failed_feeds = get_failed_feeds(feeds)

        self.assertEqual(len(failed_feeds), 1)
        self.assertEqual(failed_feeds[0]["title"], "Reuters World News")
        self.assertEqual(failed_feeds[0]["parsing_error_count"], 3246)

    def test_update_feeds_status_state_persists_latest_snapshot_and_returns_current_events(self):
        feed = {
            "id": 81,
            "title": "Reuters World News",
            "feed_url": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
            "site_url": "https://www.reuters.com/world/",
            "parsing_error_count": 3246,
            "parsing_error_message": "Failed to fetch feed because the upstream server denied access.",
            "checked_at": "2026-03-17T14:41:34.870212+08:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "feeds_status.json"

            result = update_feeds_status_state([feed], file_path=state_file, now="2026-03-18T09:00:00+08:00")

            self.assertEqual(result["snapshot"]["failed_count"], 1)
            self.assertEqual(len(result["events"]), 1)
            self.assertIn("Feed Error", result["events"][0]["title"])
            self.assertEqual(result["events"][0]["published_at"], "2026-03-18T09:00:00+08:00")

            persisted_state = load_feeds_status_state(state_file)
            self.assertEqual(persisted_state["latest_snapshot"]["failed_count"], 1)
            self.assertNotIn("events", persisted_state)

    def test_update_feeds_status_state_returns_current_events_on_every_run(self):
        feed = {
            "id": 81,
            "title": "Reuters World News",
            "feed_url": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
            "site_url": "https://www.reuters.com/world/",
            "parsing_error_count": 3246,
            "parsing_error_message": "Failed to fetch feed because the upstream server denied access.",
            "checked_at": "2026-03-17T14:41:34.870212+08:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "feeds_status.json"

            first_result = update_feeds_status_state([feed], file_path=state_file, now="2026-03-18T09:00:00+08:00")
            second_result = update_feeds_status_state([feed], file_path=state_file, now="2026-03-19T09:00:00+08:00")
            recovered_result = update_feeds_status_state([], file_path=state_file, now="2026-03-20T09:00:00+08:00")

            self.assertEqual(len(first_result["events"]), 1)
            self.assertEqual(first_result["events"][0]["published_at"], "2026-03-18T09:00:00+08:00")
            self.assertEqual(len(second_result["events"]), 1)
            self.assertEqual(second_result["events"][0]["published_at"], "2026-03-19T09:00:00+08:00")
            self.assertEqual(recovered_result["snapshot"]["failed_count"], 0)
            self.assertEqual(len(recovered_result["events"]), 0)

    def test_summary_entry_identity_title_and_time_use_current_snapshot(self):
        snapshot = {
            "generated_at": "2026-03-19T09:00:00+08:00",
            "failed_count": 3,
            "failed_feeds": [],
        }

        summary_title = build_summary_entry_title(snapshot)
        summary_dt = build_summary_entry_datetime(snapshot)

        self.assertEqual(build_summary_entry_id(snapshot), "https://feeds-status.miniflux/current/20260319090000")
        self.assertEqual(summary_title, "Feed Status Overview - 3 Failed Feeds")
        self.assertEqual(summary_dt.isoformat(), "2026-03-19T09:02:00+08:00")
        self.assertTrue(should_render_summary_entry(snapshot))
        self.assertEqual(build_summary_entry_link(snapshot), "https://feeds-status.miniflux/current#date=2026-03-19")
        self.assertFalse(should_render_summary_entry(None))

    def test_event_link_appends_date(self):
        event = {
            "link": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
            "published_at": "2026-03-18T09:00:00+08:00",
            "feed": {
                "title": "Reuters World News",
            },
        }

        self.assertEqual(
            build_event_display_link(event),
            "https://www.reutersagency.com/feed/?best-topics=world&post_type=best#date=2026-03-18",
        )

    def test_load_feeds_status_state_ignores_legacy_event_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "feeds_status.json"
            state_file.write_text(
                json.dumps(
                    {
                        "latest_snapshot": {
                            "generated_at": "2026-03-19T09:00:00+08:00",
                            "failed_count": 1,
                            "failed_feeds": [{"title": "Broken Feed"}],
                        },
                        "events": [
                            {"title": "keep", "feed": {"title": "Broken Feed"}},
                            {"title": "drop", "change_type": "recovered", "feed": {"title": "Recovered Feed"}},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            state = load_feeds_status_state(state_file)

            self.assertEqual(state["latest_snapshot"]["failed_count"], 1)
            self.assertNotIn("events", state)

    def test_fetch_failed_feeds_from_config_server(self):
        config_file = Path(__file__).resolve().parents[1] / "config.yml"
        if not config_file.exists():
            self.skipTest("config.yml not found")

        config = _read_miniflux_config(config_file)
        if not config["base_url"] or not config["api_key"]:
            self.skipTest("miniflux.base_url or miniflux.api_key is missing in config.yml")

        try:
            feeds = _fetch_feeds_from_server(config["base_url"], config["api_key"])
        except (error.URLError, TimeoutError, OSError, ValueError) as exc:
            self.skipTest(f"cannot access configured Miniflux server: {exc}")

        failed_feeds = get_failed_feeds(feeds)
        result = {
            "server": config["base_url"],
            "feed_count": len(feeds),
            "failed_count": len(failed_feeds),
            "failed_feeds": failed_feeds,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))

        self.assertIsInstance(feeds, list)


if __name__ == "__main__":
    unittest.main()
