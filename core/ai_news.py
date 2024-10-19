from datetime import datetime


def ai_news(miniflux_client):
    entries = miniflux_client.get_entries(after=datetime.now()-datetime.timedelta(days=1), limit=10000)