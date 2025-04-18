import base64
from io import BytesIO
from urllib.parse import urlparse, urlunparse

import requests
from PIL import Image
from deep_translator import GoogleTranslator

MARKETAUX_API = "https://api.marketaux.com/v1/news/all"
MARKETAUX_TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
RSS_FEEDS = [
    "https://www.lebanon24.com/Rss/News/5/%D8%A5%D9%82%D8%AA%D8%B5%D8%A7%D8%AF",
    "https://www.aljadeed.tv/Rss/News/1055/إقتصاد",
    "https://www.lbcgroup.tv/Rss/News/en/104/lebanon-economy"
]
RSS_TIMESTAMP_FMT = "%a, %d %b %Y %H:%M:%S GMT"
LANG = "en"

with open("assets/news_placeholder.jpg", "rb") as image_file:
    BASE64_NO_IMAGE = base64.b64encode(image_file.read())


def image_to_base64(url, max_size=(360, 360)):
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        image.thumbnail(max_size)
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        base64_str = base64.b64encode(img_byte_arr).decode('utf-8')
        return base64_str
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the image: {e}")
        return BASE64_NO_IMAGE
    except Exception as e:
        print(f"Error processing the image: {e}")
        return BASE64_NO_IMAGE


def remove_referrers(url):
    parsed_url = urlparse(url)
    clean_url = parsed_url._replace(query="")
    return urlunparse(clean_url)


def translate_items(items):
    for item in items:
        if item['language'] != LANG:
            translator = GoogleTranslator(item['language'], LANG)
            item['headline'] = translator.translate(item['headline'])
            item['description'] = translator.translate(item['description'])
    return items
