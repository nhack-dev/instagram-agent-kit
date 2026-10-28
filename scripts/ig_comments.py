"""コメントを集めて、返信の下書きを作り、確かめたものだけ返す。

  python3 scripts/ig_comments.py fetch --media 5 --go
      → data/reply-drafts.json に未返信のコメントを足す（reply は空・approve は false）
  （エージェントが playbooks/04-comments.md の基準で reply を書き、approve を true にする）
  python3 scripts/ig_comments.py send          # 送る予定を表示するだけ
  python3 scripts/ig_comments.py send --go     # approve=true のものだけ返信する
  python3 scripts/ig_comments.py hide --comment-id 123 --go   # 荒らしを非表示に

1回の send で返すのは20件まで・1件ごとに3秒あける（短時間に大量に返さない）。
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import json
import time

import ig
from _common import DATA, append_log, read_log

DRAFTS = DATA / "reply-drafts.json"


def load() -> list[dict]:
    return json.loads(DRAFTS.read_text(encoding="utf-8")) if DRAFTS.exists() else []


def store(rows: list[dict]) -> None:
    DATA.mkdir(exist_ok=True)
    DRAFTS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch(n_media: int, go: bool) -> None:
    _, uid, _ = ig.base(go)
    me = ig.get("me", {"fields": "username"}, go) or {}
    medias = ig.get(f"{uid}/media", {"fields": "id,caption,permalink,timestamp", "limit": str(n_media)}, go)
    if not go:
        ig.get("<MEDIA_ID>/comments", {"fields": "id,text,username,timestamp,like_count,replies{id,username}"}, go)
        print("\n（dry-run でした）")
        return
    done = {r["comment_id"] for r in read_log("replied.jsonl")}
    rows = load()
    known = {r["comment_id"] for r in rows}
    added = 0
    for m in (medias or {}).get("data", []):
        r = ig.get(f"{m['id']}/comments", {"fields": "id,text,username,timestamp,like_count,replies{id,username}",
                                            "limit": "50"}, go) or {}
        for c in r.get("data", []):
            if c["id"] in done or c["id"] in known or c.get("username") == me.get("username"):
                continue
            replied_by_me = any(x.get("username") == me.get("username") for x in (c.get("replies") or {}).get("data", []))
            if replied_by_me:
                continue
            rows.append({"comment_id": c["id"], "media_id": m["id"], "post": (m.get("caption") or "")[:40],
                         "from": c.get("username"), "text": c.get("text"), "timestamp": c.get("timestamp"),
                         "reply": "", "approve": False, "note": ""})
            added += 1
        time.sleep(0.5)
    store(rows)
    print(f"新しいコメント {added} 件を data/reply-drafts.json に足しました（未処理 {sum(1 for x in rows if not x.get('sent'))} 件）")


def send(go: bool) -> None:
    rows = load()
    todo = [r for r in rows if r.get("approve") and r.get("reply") and not r.get("sent")][:20]
    if not todo:
        print("送るものはありません（approve=true かつ reply があるものだけ送ります）")
        return
    for r in todo:
        if len(r["reply"]) > 300:
            print(f"  飛ばしました（長すぎ {len(r['reply'])} 字）: {r['comment_id']}")
            continue
        res = ig.post(f"{r['comment_id']}/replies", {"message": r["reply"]}, go)
        if go:
            r["sent"] = True
            append_log("replied.jsonl", {"comment_id": r["comment_id"], "reply_id": (res or {}).get("id"),
                                         "at": time.strftime("%Y-%m-%d %H:%M")})
            time.sleep(3)
    if go:
        store(rows)
        print(f"返信 {len(todo)} 件")
    else:
        print(f"\n（dry-run でした。返す予定 {len(todo)} 件）")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--media", type=int, default=5, help="新しい投稿から何本見るか")
    f.add_argument("--go", action="store_true")
    s = sub.add_parser("send")
    s.add_argument("--go", action="store_true")
    h = sub.add_parser("hide")
    h.add_argument("--comment-id", required=True)
    h.add_argument("--unhide", action="store_true")
    h.add_argument("--go", action="store_true")
    a = p.parse_args()
    if a.cmd == "fetch":
        fetch(a.media, a.go)
    elif a.cmd == "send":
        send(a.go)
    else:
        ig.post(a.comment_id, {"hide": "false" if a.unhide else "true"}, a.go)
        print("非表示にしました" if a.go else "（dry-run）")


if __name__ == "__main__":
    main()
