"""コメントに合言葉を書いた人へ、DM を1通だけ返す（公式の「プライベート返信」）。

公式の条件（README の「DM の決まり」も読む）：
- コメント1件につき送れるのは1通だけ
- コメントから7日以内
- 相手が返事をくれたら、そこから24時間は普通にやり取りできる
- 1時間に750回まで（投稿・リールへのプライベート返信）

設定：config/keywords.json（例は config/keywords.example.json）

  python3 scripts/ig_private_reply.py          # 送る相手と文を表示するだけ
  python3 scripts/ig_private_reply.py --go     # 本当に送る

10〜15分おきに動かす形を想定（cron の例は README）。
リアルタイムにしたい人は Webhook（comments）を受ける小さなサーバーが要ります（このキットには入れていません）。
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import json
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import ig
from _common import ROOT, append_log, read_log, read_text_arg

CONF = ROOT / "config" / "keywords.json"


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower().replace(" ", "")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--media", type=int, default=10, help="新しい投稿から何本見るか")
    p.add_argument("--go", action="store_true")
    a = p.parse_args()

    if not CONF.exists():
        sys.exit("config/keywords.json がありません。config/keywords.example.json を写して作ってください。")
    rules = json.loads(CONF.read_text(encoding="utf-8"))["rules"]
    _, uid, _ = ig.base(a.go)
    medias = ig.get(f"{uid}/media", {"fields": "id,caption,timestamp", "limit": str(a.media)}, a.go)
    if not a.go:
        ig.get("<MEDIA_ID>/comments", {"fields": "id,text,username,timestamp"}, a.go)
        ig.post_json(f"{uid}/messages", {"recipient": {"comment_id": "<COMMENT_ID>"},
                                         "message": {"text": "（keywords.json の文）"}}, a.go)
        print("\n（dry-run でした）")
        return

    me = (ig.get("me", {"fields": "username"}, a.go) or {}).get("username")
    sent = {r["comment_id"] for r in read_log("private-replies.jsonl")}
    limit_at = datetime.now(timezone.utc) - timedelta(days=7)
    n = 0
    for m in (medias or {}).get("data", []):
        r = ig.get(f"{m['id']}/comments", {"fields": "id,text,username,timestamp", "limit": "50"}, a.go) or {}
        for c in r.get("data", []):
            if c["id"] in sent or c.get("username") == me:
                continue
            ts = datetime.strptime(c["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            if ts < limit_at:
                continue  # 7日を過ぎたら送れない
            for rule in rules:
                if rule.get("media_ids") and m["id"] not in rule["media_ids"]:
                    continue
                if norm(rule["keyword"]) in norm(c.get("text")):
                    text = read_text_arg(rule.get("message"), rule.get("message_file"))
                    if len(text.encode("utf-8")) > 1000:
                        sys.exit(f"[止めました] DM の文が1000バイトを超えています: {rule['keyword']}")
                    ig.post_json(f"{uid}/messages", {"recipient": {"comment_id": c["id"]},
                                                     "message": {"text": text}}, a.go)
                    append_log("private-replies.jsonl", {"comment_id": c["id"], "keyword": rule["keyword"],
                                                         "at": time.strftime("%Y-%m-%d %H:%M")})
                    n += 1
                    time.sleep(2)
                    break
    print(f"DM を {n} 通送りました")


if __name__ == "__main__":
    main()
