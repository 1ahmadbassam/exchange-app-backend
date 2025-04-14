import datetime

import jwt

from init import SECRET_KEY


def create_jwt(user_id):
    payload = {'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=4),
        'iat': datetime.datetime.now(datetime.timezone.utc), 'sub': str(user_id)}
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def extract_auth_jwt(authenticated_request):
    auth_header = authenticated_request.headers.get('Authorization')
    if auth_header:
        return auth_header.split(" ")[1].strip()
    else:
        return None


def decode_jwt(token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return payload['sub']
