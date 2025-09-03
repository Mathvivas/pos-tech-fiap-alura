from functools import wraps
import config
import jwt
import datetime

def create_token(username):
    payload = {
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return token

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Pegar token do header Authorization: Bearer <token>
        # Decodificar e checar expiração
        return f(*args, **kwargs)
    return decorated