import base64
from io import BytesIO

import boto3
from gtts import gTTS

from init import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_SESSION_TOKEN

RATE_TEXT = "{}"
RATE_NONE = "There is no recorded rate data in the past {}."
RATE_PROMPT = ("Summarize the below information about the USD-LBP and LBP-USD exchange rates in the past {} in a few "
               "sentences. Be sure to highlight trends for both, with dates. \n")

VOLUME_TEXT = "{}"
VOLUME_NONE = "There is no recorded volume data in the past {}."
VOLUME_PROMPT = ("Summarize the below information about the USD-LBP and LBP-USD exchange rate volume in the past {} "
                 "in a few sentences. Be sure to highlight trends for both volumes, with dates. \n")

WALLET_TEXT = "Hello {}! Your wallet currently contains {} USD and {} LBP. {}"
WALLET_NONE = "You have not made any recorded wallet transactions in the past {}."
WALLET_PROMPT = ("Can you summarize the below wallet transactions made in the past {} in a few sentences? "
                 "Talk to me as the wallet holder. "
                 "Start directly with the summary in a natural way. "
                 "Make sure to include both LBP, USD, and date information. \n")

NEWS_TEXT = "{}"
NEWS_NONE = "No news articles have been recorded in the past {}."
NEWS_PROMPT = ("Summarize the below news articles published in the past {} in a few sentences. "
               "Start directly with the summary in a natural way. "
               "Make sure to tend to summarizing the impact on the LBP-USD exchange rate "
               "as well as the lebanese economy. \n")


def text_tts_aws(text):
    polly = boto3.client('polly',
                         aws_access_key_id=AWS_ACCESS_KEY,
                         aws_secret_access_key=AWS_SECRET_KEY,
                         aws_session_token=AWS_SESSION_TOKEN
                         )
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Matthew'
    )
    audio_stream = BytesIO(response['AudioStream'].read())
    audio_stream.seek(0)
    audio_base64 = base64.b64encode(audio_stream.read()).decode('utf-8')
    return audio_base64, "audio/mp3"


def text_tts_gtts(text):
    tts = gTTS(text=text, lang='en')
    audio_stream = BytesIO()
    tts.write_to_fp(audio_stream)
    audio_stream.seek(0)
    audio_base64 = base64.b64encode(audio_stream.read()).decode('utf-8')
    return audio_base64, "audio/mp3"


def text_tts(text):
    if AWS_ACCESS_KEY and AWS_SECRET_KEY and AWS_SESSION_TOKEN:
        return text_tts_aws(text)
    else:
        return text_tts_gtts(text)
