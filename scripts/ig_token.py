"""アクセストークンを長期（60日）に替える・延ばす。

  python3 scripts/ig_token.py exchange --go   # 短期（1時間）→ 長期（60日）
  python3 scripts/ig_token.py refresh --go    # 長期をさらに60日延ばす（発行から24時間たってから）

アプリの管理画面の「トークンを生成」で作ったトークンは最初から長期なので exchange は要りません。
新しいトークンは画面に出すだけです。.env の IG_ACCESS_TOKEN を自分で書き換えてください。
"""

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401

import argparse
import json

from _common import call, env, load_env

load_env()
p = argparse.ArgumentParser()
p.add_argument("action", choices=["exchange", "refresh"])
p.add_argument("--go", action="store_true")
a = p.parse_args()

token = env("IG_ACCESS_TOKEN", a.go)
if a.action == "exchange":
    r = call("GET", "https://graph.instagram.com/access_token",
             {"grant_type": "ig_exchange_token", "client_secret": env("IG_APP_SECRET", a.go),
              "access_token": token}, go=a.go)
else:
    r = call("GET", "https://graph.instagram.com/refresh_access_token",
             {"grant_type": "ig_refresh_token", "access_token": token}, go=a.go)
if r:
    days = int(r.get("expires_in", 0)) // 86400
    print(json.dumps({"token_type": r.get("token_type"), "expires_in_days": days}, ensure_ascii=False))
    print("新しいトークン（.env の IG_ACCESS_TOKEN に貼る・人に見せない）:")
    print(r.get("access_token"))
