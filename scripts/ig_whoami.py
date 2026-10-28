"""つながっているか確かめる（最初の10分で使う）。

  python3 scripts/ig_whoami.py          # 呼ぶ予定のリクエストを表示するだけ
  python3 scripts/ig_whoami.py --go     # 本当に呼ぶ
"""

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401

import argparse
import json

import ig

p = argparse.ArgumentParser()
p.add_argument("--go", action="store_true", help="本当に API を呼ぶ")
a = p.parse_args()

me = ig.get("me", {"fields": "user_id,username,account_type,followers_count,media_count"}, a.go)
if me:
    print(json.dumps(me, ensure_ascii=False, indent=2))
    print("\n→ .env の IG_USER_ID には上の user_id を入れてください。")
