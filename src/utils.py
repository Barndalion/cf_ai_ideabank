from urllib.parse import urlparse, parse_qs
from uuid import uuid4

def get_chat_id_from_url(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    uid = qs.get("chat_id", [None])[0]

    return uid

def gen_chat_uuid():
    return f"chat:{str(uuid4())}"

def gen_idea_uuid():
    return f"idea:{str(uuid4())}"

def get_query_param(url, param):
    return parse_qs(urlparse(url).query).get(param, [None])[0]

def gen_user_uuid():
    return f"user:{str(uuid4())}"