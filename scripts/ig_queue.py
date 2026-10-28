"""予約投稿（API に予約の機能は無いので、このキットが時刻を見て出す）。

  python3 scripts/ig_queue.py add --at "2026-11-01 19:00" --kind reel \
      --media https://example.com/v.mp4 --caption-file drafts/2026-11-01-reel.md
  python3 scripts/ig_queue.py list
  python3 scripts/ig_queue.py run          # 時刻が来たものを表示するだけ
  python3 scripts/ig_queue.py run --go     # 時刻が来たものを本当に投稿する

run --go を 10分おきに動かす（cron の例は README）。投稿したものは queue/done/ に移ります。
時刻は「パソコンの時計の時刻」で書きます。
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from _common import ROOT, read_text_arg
from ig_check import caption_of

Q = ROOT / "queue"
DONE = Q / "done"


def add(a) -> None:
    at = datetime.strptime(a.at, "%Y-%m-%d %H:%M")
    Q.mkdir(exist_ok=True)
    item = {"at": at.strftime("%Y-%m-%d %H:%M"), "kind": a.kind, "media": a.media,
            "caption_file": a.caption_file, "cover_url": a.cover_url}
    name = Q / f"{at.strftime('%Y%m%d-%H%M')}-{a.kind}.json"
    if name.exists():
        sys.exit(f"同じ時刻・同じ種類の予約があります: {name.name}")
    name.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"予約しました: {name.relative_to(ROOT)}")


def items() -> list[Path]:
    return sorted(p for p in Q.glob("*.json"))


def run(go: bool) -> None:
    from ig_publish import publish  # 予約が無いときは読み込まない
    now = datetime.now()
    due = [p for p in items() if datetime.strptime(json.loads(p.read_text())["at"], "%Y-%m-%d %H:%M") <= now]
    if not due:
        print("時刻が来た予約はありません。")
        return
    for p in due[:3]:  # 1回に出すのは3本まで（まとめて出しすぎない）
        it = json.loads(p.read_text(encoding="utf-8"))
        print(f"→ {p.name}")
        cap = caption_of(read_text_arg(None, it["caption_file"])) if it.get("caption_file") else ""
        mid = publish(it["kind"], it["media"], cap, go, it.get("cover_url"))
        if go and mid:
            DONE.mkdir(parents=True, exist_ok=True)
            it["media_id"] = mid
            (DONE / p.name).write_text(json.dumps(it, ensure_ascii=False, indent=2), encoding="utf-8")
            p.unlink()
            time.sleep(5)


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add")
    s.add_argument("--at", required=True, help='"YYYY-MM-DD HH:MM"')
    s.add_argument("--kind", required=True, choices=["image", "carousel", "reel", "story"])
    s.add_argument("--media", action="append", required=True)
    s.add_argument("--caption-file")
    s.add_argument("--cover-url")
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("--go", action="store_true")
    a = p.parse_args()
    if a.cmd == "add":
        add(a)
    elif a.cmd == "list":
        for x in items():
            it = json.loads(x.read_text(encoding="utf-8"))
            print(f"{it['at']}  {it['kind']:8} {it.get('caption_file') or ''}")
        print(f"予約 {len(items())} 件")
    else:
        run(a.go)


if __name__ == "__main__":
    main()
