import json

from google import genai

from init import GEMINI_KEY
from util.news.ai import SCORING_PROMPT, NewsImpact


def score_news(news, trial: int = 5):
    simplified_news = [
        {
            "headline": x["headline"],
            "description": x["description"],
            "timestamp": x["timestamp"]
        }
        for x in news
    ]
    scoring = []
    for i in range(0, len(simplified_news), trial):
        client = genai.Client(api_key=GEMINI_KEY)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=SCORING_PROMPT + '{' + str(simplified_news[i:i + trial]) + '}',
            config={
                'response_mime_type': 'application/json',
                'response_schema': list[NewsImpact],
            },
        )
        scoring.extend(json.loads(response.text))
    return scoring
