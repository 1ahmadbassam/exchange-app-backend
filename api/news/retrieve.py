import datetime
from urllib.parse import urlparse

import requests
from rss_parser import RSSParser

from api.news.ai import score_news
from init import MARKETAUX_KEY, db, scheduler, app
from model.news import News
from util.news.base import (MARKETAUX_API, image_to_base64, RSS_FEEDS, remove_referrers,
                            RSS_TIMESTAMP_FMT, LANG, translate_items, MARKETAUX_TIMESTAMP_FMT, clean_html_data)
from util.news.rss import RSS


def retrieve_news_marketaux(after: datetime.datetime = None, limit: int = 3):
    def retrieve_raw_marketaux():
        api = MARKETAUX_API
        params = {
            "api_token": MARKETAUX_KEY,
            "countries": "global",
            "filter_entities": True,
            "language": LANG,
            "limit": limit
        }
        if after:
            params['published_after'] = after.strftime('%Y-%m-%dT%H:%M:%S')
        response = requests.get(api, params=params, timeout=20)
        return response.json()

    json_data = retrieve_raw_marketaux()
    data = json_data.get('data', None)

    news = []
    if data:
        for entry in data:
            headline = clean_html_data(entry.get('title', None))
            description = clean_html_data(entry.get('description', None))
            url = entry.get('url', None)
            image_url = entry.get('image_url', None)
            image = image_to_base64(image_url)
            timestamp = entry.get('published_at', None)
            if timestamp:
                timestamp = datetime.datetime.strptime(timestamp, MARKETAUX_TIMESTAMP_FMT)
            source = entry.get('source', None)
            news.append({
                "headline": headline,
                "description": description,
                "source": source,
                "url": url,
                "image": image,
                "timestamp": timestamp,
                "language": LANG
            })
    return news


def retrieve_news_rss(after: datetime.datetime = None, limit: int = 3):
    news = []
    for feed in RSS_FEEDS:
        rss_raw = requests.get(feed, timeout=20)
        rss = RSSParser.parse(rss_raw.text, schema=RSS)
        language = rss.channel.language.content
        source = urlparse(feed).netloc
        for i in range(min(len(rss.channel.items), limit)):
            item = rss.channel.items[i]
            headline = clean_html_data(item.title.content)
            if item.description:
                description = clean_html_data(item.description.content)
            else:
                description = ""
            url = remove_referrers(item.links[0].content)
            if item.media:
                image = item.media.attributes['url']
            else:
                image = ""
            image = image_to_base64(image)
            timestamp = datetime.datetime.strptime(item.pub_date.content, RSS_TIMESTAMP_FMT)
            if after and timestamp < after:
                break
            news.append({
                "headline": headline,
                "description": description,
                "source": source,
                "url": url,
                "image": image,
                "timestamp": timestamp,
                "language": language[:2] if len(language) > 2 else language
            })
    return news


def retrieve_news(after: datetime.datetime = None, limit: int = 3):
    news = []
    news.extend(retrieve_news_rss(after, limit))
    news.extend(retrieve_news_marketaux(after, limit))
    if news:
        news = translate_items(news)
        scoring = score_news(news)
        for news_item, score_item in zip(news, scoring):
            news_item.update(score_item)
    return news


@scheduler.task('interval', id='news_update', minutes=15)
def news_update():
    with app.app_context():
        last_refresh = db.session.query(News).order_by(News.timestamp.desc()).first().timestamp
        c = db.session.query(News).count()
        news = retrieve_news(last_refresh)
        if c + len(news) > 50:
            items_to_delete = (c + len(news)) - 50
            old_news = db.session.query(News).order_by(News.timestamp.asc()).limit(items_to_delete).all()
            for item in old_news:
                db.session.delete(item)
        for news_item in news:
            try:
                db_item = News(headline=news_item['headline'],
                               content=news_item['description'],
                               source=news_item['source'],
                               impact=int(news_item['impact_score']),
                               impact_summary=news_item['impact_reasoning'],
                               confidence=float(news_item['confidence']),
                               timestamp=news_item['timestamp'],
                               url=news_item['url'],
                               image=news_item['image'])
                db.session.add(db_item)
                db.session.commit()
            except Exception as e:
                print("Exception occurred:", e)


def news_update_initial():
    if db.session.query(News).count() > 0:
        return
    news_update()
