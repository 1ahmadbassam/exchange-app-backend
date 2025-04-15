import datetime

import jwt
from itsdangerous import SignatureExpired, BadSignature, URLSafeTimedSerializer

from init import SECURITY_PASSWORD_SALT, SECRET_KEY, tz


def create_jwt(user_id):
    payload = {'exp': datetime.datetime.now(tz) + datetime.timedelta(days=4),
               'iat': datetime.datetime.now(tz), 'sub': str(user_id)}
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


def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(email, salt=SECURITY_PASSWORD_SALT)


def confirm_verification_token(token, expiration=900):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    try:
        email = serializer.loads(token, salt=SECURITY_PASSWORD_SALT, max_age=expiration)
        return True, email
    except SignatureExpired:
        return False, "Expired token"
    except BadSignature:
        return False, "Invalid token"
