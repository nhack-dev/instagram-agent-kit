"""Instagram API の入口をまとめたもの。

既定は「Instagram ログインの Instagram API」（graph.instagram.com・Facebook ページ不要）。
Facebook ログインの形で使う人は .env で IG_HOST=graph.facebook.com にする。
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import os

from _common import call, env, load_env

load_env()

VERSION = os.environ.get("IG_API_VERSION", "v26.0")
HOST = os.environ.get("IG_HOST", "graph.instagram.com")


def base(go: bool) -> tuple[str, str, str]:
    """(URLの頭, IGのユーザーID, アクセストークン) を返す。"""
    token = env("IG_ACCESS_TOKEN", go)
    user_id = env("IG_USER_ID", go)
    host = HOST if HOST.startswith("http") else f"https://{HOST}"
    return f"{host}/{VERSION}", user_id, token


def get(path: str, params: dict, go: bool):
    root, _, token = base(go)
    return call("GET", f"{root}/{path.lstrip('/')}", {**params, "access_token": token}, go=go)


def post(path: str, params: dict, go: bool):
    root, _, token = base(go)
    return call("POST", f"{root}/{path.lstrip('/')}", {**params, "access_token": token}, go=go)


def post_json(path: str, body: dict, go: bool):
    root, _, token = base(go)
    return call("POST", f"{root}/{path.lstrip('/')}", body=body, go=go, json_body=True,
                headers={"Authorization": f"Bearer {token}"})


def delete(path: str, go: bool):
    root, _, token = base(go)
    return call("DELETE", f"{root}/{path.lstrip('/')}", {"access_token": token}, go=go)
