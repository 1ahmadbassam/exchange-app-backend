from google import genai
from google.genai import types

from init import GEMINI_KEY
from model.news import NewsSchema
from model.wallet import WalletTransactionSchema
from util.accessibility.summarize import (WALLET_NONE, WALLET_PROMPT, NEWS_NONE, NEWS_PROMPT,
                                          RATE_NONE, RATE_PROMPT, VOLUME_NONE, VOLUME_PROMPT)

wallet_transactions_schema = WalletTransactionSchema(many=True)
news_schema = NewsSchema(many=True)


def summarize_rate_text(rates, period):
    if not rates:
        return RATE_NONE.format(period)

    client = genai.Client(api_key=GEMINI_KEY)
    # rt is already a proper python object
    rt = rates

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[RATE_PROMPT.format(period) + '{' + str(rt) + '}'],
        config=types.GenerateContentConfig(
            temperature=0.8
        )
    )

    return response.text


def summarize_volume_text(volumes, period):
    if not volumes:
        return VOLUME_NONE.format(period)

    client = genai.Client(api_key=GEMINI_KEY)
    # vl is already a proper python object
    vl = volumes

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[VOLUME_PROMPT.format(period) + '{' + str(vl) + '}'],
        config=types.GenerateContentConfig(
            temperature=0.8
        )
    )

    return response.text


def summarize_wallet_text(wallet_transactions, period):
    if not wallet_transactions:
        return WALLET_NONE.format(period)

    client = genai.Client(api_key=GEMINI_KEY)
    wl = wallet_transactions_schema.dump(wallet_transactions)
    for entry in wl:
        del entry['user_id']
        del entry['id']

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[WALLET_PROMPT.format(period) + '{' + str(wl) + '}'],
        config=types.GenerateContentConfig(
            temperature=0.8
        )
    )

    return response.text


def summarize_news_text(news, period):
    if not news:
        return NEWS_NONE.format(period)

    client = genai.Client(api_key=GEMINI_KEY)
    nw = news_schema.dump(news)
    for entry in nw:
        del entry['id']
        del entry['source']
        del entry['url']
        del entry['image']

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[NEWS_PROMPT.format(period) + '{' + str(nw) + '}'],
        config=types.GenerateContentConfig(
            temperature=0.8
        )
    )

    return response.text
