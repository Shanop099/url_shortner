import string
import random
from datetime import datetime

def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def is_expired(expiry):
    if expiry is None:
        return False
    return datetime.utcnow() > datetime.fromisoformat(expiry)