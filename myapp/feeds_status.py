from datetime import datetime

from feedgen.feed import FeedGenerator

from services.feeds_status_service import (
    FEEDS_STATUS_FEED_ID,
    FEEDS_STATUS_FEED_TITLE,
    build_error_events,
    build_event_display_content,
    build_event_display_link,
    build_event_display_title,
    build_summary_entry_id,
    build_summary_entry_link,
    build_summary_entry_datetime,
    build_summary_entry_title,
    load_feeds_status_state,
    render_failed_feeds_summary_html,
    should_render_summary_entry,
)
from myapp import app


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@app.route("/rss/feeds-status", methods=["GET"])
def miniflux_feeds_status():
    state = load_feeds_status_state()
    snapshot = state.get("latest_snapshot")

    fg = FeedGenerator()
    fg.id(FEEDS_STATUS_FEED_ID)
    fg.title(FEEDS_STATUS_FEED_TITLE)
    fg.subtitle("Powered by miniflux-ai")
    fg.author({"name": "miniflux-ai"})
    fg.link(href=FEEDS_STATUS_FEED_ID, rel="self")

    if should_render_summary_entry(snapshot):
        summary_entry = fg.add_entry()
        summary_entry.id(build_summary_entry_id(snapshot))
        summary_entry.link(href=build_summary_entry_link(snapshot))
        summary_entry.title(build_summary_entry_title(snapshot))
        summary_entry.description(render_failed_feeds_summary_html(snapshot))
        summary_dt = build_summary_entry_datetime(snapshot)
        if summary_dt:
            summary_entry.published(summary_dt)
            fg.updated(summary_dt)

    for event in build_error_events(snapshot):
        entry = fg.add_entry()
        entry.id(event["id"])
        entry.link(href=build_event_display_link(event))
        entry.title(build_event_display_title(event))
        entry.description(build_event_display_content(event))
        published_dt = _parse_datetime(event.get("published_at"))
        if published_dt:
            entry.published(published_dt)

    return fg.rss_str(pretty=True)
