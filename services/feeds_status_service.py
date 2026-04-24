import hashlib
import html
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin


logger = logging.getLogger(__name__)

FEEDS_STATUS_FILE = Path("feeds_status.json")
FEEDS_STATUS_FEED_ID = "https://feeds-status.miniflux"
FEEDS_STATUS_FEED_TITLE = "Miniflux Feeds Status"
FEEDS_STATUS_FEED_PATH = "/rss/feeds-status"
SUMMARY_ENTRY_ID = f"{FEEDS_STATUS_FEED_ID}/current"
SUMMARY_ENTRY_OFFSET_MINUTES = 2


def _now_iso(now=None):
    if now is None:
        return datetime.now().astimezone().isoformat()
    if isinstance(now, str):
        return now
    return now.isoformat()


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_time(value):
    dt = _parse_datetime(value)
    if not dt:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")


def _format_date(value):
    dt = _parse_datetime(value)
    if not dt:
        return "unknown-date"
    return dt.strftime("%Y-%m-%d")


def _build_link(url):
    if not url:
        return "-"
    escaped = html.escape(url, quote=True)
    return f'<a href="{escaped}">{escaped}</a>'


def is_failed_feed(feed):
    if bool(feed.get("disabled")):
        return False
    return _safe_int(feed.get("parsing_error_count")) > 0 or bool(_text(feed.get("parsing_error_message")))


def normalize_failed_feed(feed):
    return {
        "id": feed.get("id"),
        "title": _text(feed.get("title")) or _text(feed.get("feed_url")) or "Untitled feed",
        "feed_url": _text(feed.get("feed_url")),
        "site_url": _text(feed.get("site_url")),
        "checked_at": _text(feed.get("checked_at")),
        "parsing_error_count": _safe_int(feed.get("parsing_error_count")),
        "parsing_error_message": _text(feed.get("parsing_error_message")),
    }


def get_failed_feeds(feeds):
    failed_feeds = [normalize_failed_feed(feed) for feed in (feeds or []) if is_failed_feed(feed)]
    return sorted(
        failed_feeds,
        key=lambda item: (-item["parsing_error_count"], item["title"].lower(), item["feed_url"]),
    )


def build_snapshot(failed_feeds, now=None):
    return {
        "generated_at": _now_iso(now),
        "failed_count": len(failed_feeds),
        "failed_feeds": failed_feeds,
    }


def load_feeds_status_state(file_path=FEEDS_STATUS_FILE):
    path = Path(file_path)
    if not path.exists():
        return {"latest_snapshot": None}

    try:
        with path.open("r", encoding="utf-8") as file:
            state = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read feeds status file %s: %s", path, exc)
        return {"latest_snapshot": None}

    if not isinstance(state, dict):
        return {"latest_snapshot": None}

    return {
        "latest_snapshot": state.get("latest_snapshot"),
    }


def save_feeds_status_state(state, file_path=FEEDS_STATUS_FILE):
    path = Path(file_path)
    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)


def update_feeds_status_state(feeds, file_path=FEEDS_STATUS_FILE, now=None):
    failed_feeds = get_failed_feeds(feeds)
    current_snapshot = build_snapshot(failed_feeds, now)

    updated_state = {
        "latest_snapshot": current_snapshot,
    }
    save_feeds_status_state(updated_state, file_path=file_path)

    return {
        "state": updated_state,
        "snapshot": current_snapshot,
    }


def collect_feeds_status(miniflux_client, file_path=FEEDS_STATUS_FILE, now=None):
    logger.info("Collecting feeds status from Miniflux")
    feeds = miniflux_client.get_feeds()
    result = update_feeds_status_state(feeds, file_path=file_path, now=now)
    logger.info(
        "Collected feeds status: %s failed feeds",
        result["snapshot"]["failed_count"],
    )
    return result


def ensure_miniflux_feed(miniflux_client, feed_url, feed_name, category_id=1):
    if not feed_url:
        logger.warning("Skipping %s feed creation because the url is not configured", feed_name)
        return

    feeds = miniflux_client.get_feeds()
    if any(item.get("feed_url") == feed_url for item in feeds):
        return

    try:
        miniflux_client.create_feed(category_id=category_id, feed_url=feed_url)
        logger.info("Successfully created the %s feed in Miniflux!", feed_name)
    except Exception as exc:
        logger.error("Failed to create the %s feed in Miniflux: %s", feed_name, exc)


def refresh_miniflux_feed(miniflux_client, feed_url, feed_name):
    if not feed_url:
        return

    feeds = miniflux_client.get_feeds()
    feed_id = next((item["id"] for item in feeds if item.get("feed_url") == feed_url), None)
    if not feed_id:
        logger.warning("Cannot refresh the %s feed because it is not subscribed in Miniflux yet", feed_name)
        return

    miniflux_client.refresh_feed(feed_id)
    logger.info("Successfully refreshed the %s feed in Miniflux!", feed_name)


def generate_feeds_status(miniflux_client, feeds_status_base_url, file_path=FEEDS_STATUS_FILE, now=None):
    result = collect_feeds_status(miniflux_client, file_path=file_path, now=now)
    refresh_miniflux_feed(
        miniflux_client,
        resolve_feeds_status_url(feeds_status_base_url),
        "feeds_status",
    )
    return result


def render_failed_feeds_summary_html(snapshot):
    snapshot = snapshot or {"generated_at": "", "failed_count": 0, "failed_feeds": []}
    failed_feeds = snapshot.get("failed_feeds", [])
    generated_at = html.escape(_format_time(snapshot.get("generated_at")))
    header = (
        "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#102a43;\">"
        f"<p style=\"margin:0 0 8px;font-size:16px;\"><strong>Current Failed Feeds:</strong> {snapshot.get('failed_count', 0)}</p>"
        f"<p style=\"margin:0 0 16px;color:#486581;\">Last Checked At: {generated_at}</p>"
    )

    if not failed_feeds:
        return (
            header
            + "<div style=\"padding:16px;border:1px solid #d9e2ec;border-radius:12px;background:#f8fbff;\">"
            "No failed feeds right now.</div></div>"
        )

    rows = []
    for index, feed in enumerate(failed_feeds, start=1):
        rows.append(
            "<tr>"
            f"<td style=\"padding:10px 12px;border:1px solid #e4ebf3;\">{index}</td>"
            f"<td style=\"padding:10px 12px;border:1px solid #e4ebf3;\">{html.escape(feed['title'])}</td>"
            f"<td style=\"padding:10px 12px;border:1px solid #e4ebf3;text-align:center;\">{feed['parsing_error_count']}</td>"
            f"<td style=\"padding:10px 12px;border:1px solid #e4ebf3;\">{html.escape(feed['parsing_error_message'] or '-')}</td>"
            f"<td style=\"padding:10px 12px;border:1px solid #e4ebf3;white-space:nowrap;\">{html.escape(_format_time(feed.get('checked_at')))}</td>"
            "</tr>"
        )

    table = (
        "<div style=\"overflow-x:auto;border:1px solid #d9e2ec;border-radius:12px;\">"
        "<table style=\"width:100%;border-collapse:collapse;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;\">"
        "<thead style=\"background:linear-gradient(90deg,#d9f0ff,#eef7ff);color:#102a43;\">"
        "<tr>"
        "<th style=\"padding:12px;text-align:left;border:1px solid #d9e2ec;\">#</th>"
        "<th style=\"padding:12px;text-align:left;border:1px solid #d9e2ec;\">Title</th>"
        "<th style=\"padding:12px;text-align:center;border:1px solid #d9e2ec;\">Failure Count</th>"
        "<th style=\"padding:12px;text-align:left;border:1px solid #d9e2ec;\">Error Message</th>"
        "<th style=\"padding:12px;text-align:left;border:1px solid #d9e2ec;\">Last Checked</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div></div>"
    )
    return header + table


def build_summary_entry_title(snapshot):
    failed_count = (snapshot or {}).get("failed_count", 0)
    return f"Feed Status Overview - {failed_count} Failed Feeds"


def build_summary_entry_id(snapshot):
    generated_at = (snapshot or {}).get("generated_at")
    dt = _parse_datetime(generated_at)
    if dt:
        return f"{SUMMARY_ENTRY_ID}/{dt.strftime('%Y%m%d%H%M%S')}"

    generated_text = _text(generated_at)
    if not generated_text:
        return SUMMARY_ENTRY_ID

    digest = hashlib.sha1(generated_text.encode("utf-8")).hexdigest()[:16]
    return f"{SUMMARY_ENTRY_ID}/{digest}"


def should_render_summary_entry(snapshot):
    return bool((snapshot or {}).get("generated_at"))


def build_summary_entry_datetime(snapshot):
    dt = _parse_datetime((snapshot or {}).get("generated_at"))
    if not dt:
        return None
    return dt + timedelta(minutes=SUMMARY_ENTRY_OFFSET_MINUTES)


def build_entry_link(base_url, generated_at):
    link_base = _text(base_url) or FEEDS_STATUS_FEED_ID
    return f"{link_base}#date={_format_date(generated_at)}"


def build_summary_entry_link(snapshot):
    return build_entry_link(SUMMARY_ENTRY_ID, (snapshot or {}).get("generated_at"))


def resolve_feeds_status_url(base_url):
    if not base_url:
        return None
    return urljoin(base_url.rstrip("/") + "/", FEEDS_STATUS_FEED_PATH.lstrip("/"))
