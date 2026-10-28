"""数字を取る（投稿ごと・アカウント全体）→ data/ に CSV と JSON。

  python3 scripts/ig_insights.py --limit 30 --go

投稿ごとの数字（公式の名前）：views reach likes comments shares saved total_interactions
リールだけ：ig_reels_avg_watch_time（平均視聴・ミリ秒） ig_reels_video_view_total_time
「impressions」「plays」は廃止なので使いません。
数字は最大48時間遅れることがあります。投稿から48時間たってから比べてください。
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import csv
import time

import ig
from _common import DATA, ApiError, save_json, today

BASE = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions"]
REELS = ["ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]
ACCOUNT = ["reach", "views", "accounts_engaged", "total_interactions", "likes", "comments", "shares", "saves"]


def metrics_of(media_id: str, names: list[str], go: bool) -> dict:
    """まとめて取る。だめなら1つずつ取り、取れない名前は空にする。"""
    try:
        r = ig.get(f"{media_id}/insights", {"metric": ",".join(names)}, go)
        return {d["name"]: (d.get("values") or [{}])[0].get("value") for d in (r or {}).get("data", [])}
    except ApiError:
        out = {}
        for n in names:
            try:
                r = ig.get(f"{media_id}/insights", {"metric": n}, go)
                out[n] = (r["data"][0].get("values") or [{}])[0].get("value")
            except (ApiError, KeyError, IndexError):
                out[n] = None
        return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=30, help="新しい順に何本見るか")
    p.add_argument("--go", action="store_true")
    a = p.parse_args()
    _, uid, _ = ig.base(a.go)

    r = ig.get(f"{uid}/media", {"fields": "id,caption,media_type,media_product_type,timestamp,permalink",
                                "limit": str(min(a.limit, 100))}, a.go)
    if not a.go:
        ig.get("<MEDIA_ID>/insights", {"metric": ",".join(BASE + REELS)}, a.go)
        now = int(time.time())
        ig.get(f"{uid}/insights", {"metric": ",".join(ACCOUNT), "period": "day", "metric_type": "total_value",
                                   "since": str(now - 7 * 86400), "until": str(now)}, a.go)
        print("\n（dry-run でした。--go で取ります）")
        return

    rows = []
    for m in (r or {}).get("data", [])[: a.limit]:
        names = BASE + (REELS if m.get("media_product_type") == "REELS" else [])
        vals = metrics_of(m["id"], names, a.go)
        rows.append({"id": m["id"], "timestamp": m.get("timestamp"), "type": m.get("media_product_type") or m.get("media_type"),
                     "permalink": m.get("permalink"), "caption_head": (m.get("caption") or "").splitlines()[0][:40] if m.get("caption") else "",
                     **vals})
        time.sleep(0.5)

    now = int(time.time())
    acct = {}
    for n in ACCOUNT:
        try:
            x = ig.get(f"{uid}/insights", {"metric": n, "period": "day", "metric_type": "total_value",
                                           "since": str(now - 7 * 86400), "until": str(now)}, a.go)
            acct[n] = ((x["data"][0].get("total_value") or {}).get("value"))
        except (ApiError, KeyError, IndexError):
            acct[n] = None

    DATA.mkdir(exist_ok=True)
    path = DATA / f"insights-{today()}.csv"
    keys = ["id", "timestamp", "type", "permalink", "caption_head"] + BASE + REELS
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    save_json(f"account-{today()}.json", {"last_7_days": acct})
    print(f"投稿 {len(rows)} 本 → {path.relative_to(path.parent.parent)}")
    print("アカウント（直近7日）:", acct)


if __name__ == "__main__":
    main()
