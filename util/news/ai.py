from pydantic import BaseModel

SCORING_PROMPT = ('For the following news headlines and descriptions given below in JSON format, rate the impact of '
                  'each on the LBP-USD exchange rate and Lebanese exchange market over 100 as of today, taking the  '
                  'timestamp of each article into account. In addition to the impact score, you must also provide  '
                  'the impact reasoning in English behind the score as well as a confidence level between 0.0 and 1.0. '
                  'Rate each headline individually, do not link any two together, keep the reasoning as neutral '
                  'and human-like as possible.' '\n')


class NewsImpact(BaseModel):
    impact_score: int
    impact_reasoning: str
    confidence: float
