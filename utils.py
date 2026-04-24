import random
import string
from datetime import datetime

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def is_expired(expiry):
    if not expiry:
        return False
    try:
        return datetime.utcnow() > datetime.fromisoformat(expiry)
    except:
        return False