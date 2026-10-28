"""Instagram に投稿する（画像・カルーセル・リール・ストーリーズ）。

公式の流れ：① 入れ物（コンテナ）を作る → ② status_code が FINISHED になるまで待つ → ③ media_publish
画像・動画は「インターネットから見られるURL」に置いておく必要があります（Meta が取りに来ます）。
画像は JPEG だけ。カルーセルは2〜20枚。

  # 何が送られるか見るだけ（既定）
  python3 scripts/ig_publish.py --kind reel --media https://example.com/v.mp4 --caption-file drafts/x.md
  # 本当に投稿する
  python3 scripts/ig_publish.py --kind reel --media https://example.com/v.mp4 --caption-file drafts/x.md --go

--kind: image / carousel / reel / story
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import sys
import time

import ig
from _common import ApiError, append_log, read_text_arg
from ig_check import caption_of, check

VIDEO_EXT = (".mp4", ".mov")


def is_video(url: str) -> bool:
    return url.lower().split("?")[0].endswith(VIDEO_EXT)


def wait_finished(container_id: str, go: bool, interval: int = 60, tries: int = 5) -> None:
    """公式のすすめ：1分に1回・最大5分まで status_code を見る。"""
    if not go:
        ig.get(container_id, {"fields": "status_code"}, go)
        return
    for i in range(tries + 1):
        r = ig.get(container_id, {"fields": "status_code"}, go) or {}
        code = r.get("status_code")
        print(f"  状態 {container_id}: {code}")
        if code in ("FINISHED", "PUBLISHED"):
            return
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"[止めました] 入れ物が {code} になりました。動画の形式（MP4/MOV・3秒〜15分）やURLを確かめてください。")
        if i < tries:
            time.sleep(interval)
    sys.exit("[止めました] 5分待っても FINISHED になりません。あとで同じコマンドをもう一度。")


def quota(go: bool) -> None:
    """24時間の投稿数（API の上限は config.quota_total に出る）。"""
    _, uid, _ = ig.base(go)
    try:
        r = ig.get(f"{uid}/content_publishing_limit", {"fields": "quota_usage,config"}, go)
    except ApiError as e:
        print(f"  （投稿数の確認はできませんでした：{e.status}。投稿は続けます）")
        return
    if r and r.get("data"):
        d = r["data"][0]
        total = (d.get("config") or {}).get("quota_total")
        print(f"  直近24時間の投稿 {d.get('quota_usage')} 本 ／ 上限 {total} 本")
        if total and d.get("quota_usage", 0) >= total:
            sys.exit("[止めました] 24時間の上限に達しています。")


def publish(kind: str, media: list[str], caption: str, go: bool, cover_url: str | None = None,
            share_to_feed: bool = True, alt_text: str | None = None, thumb_offset: int | None = None) -> str | None:
    _, uid, _ = ig.base(go)
    if kind != "story":
        problems = check(caption)
        for x in problems:
            print("  " + x)
        if any(x.startswith("NG") for x in problems):
            sys.exit("[止めました] キャプションが公式の上限を超えています。")
    for u in media:
        if not u.startswith("https://") and not u.startswith("<"):
            sys.exit(f"[止めました] URL は https:// で始まる公開URLにしてください: {u}")
        if not is_video(u) and not u.lower().split("?")[0].endswith((".jpg", ".jpeg")):
            print(f"  注意: 画像は JPEG だけです（{u}）。PNG なら JPEG に変換してから置いてください。")

    quota(go)
    params: dict = {}
    if kind == "image":
        if len(media) != 1:
            sys.exit("image は1枚だけ。複数ならカルーセル（--kind carousel）")
        params = {"image_url": media[0], "caption": caption}
        if alt_text:
            params["alt_text"] = alt_text
    elif kind == "reel":
        params = {"media_type": "REELS", "video_url": media[0], "caption": caption,
                  "share_to_feed": "true" if share_to_feed else "false"}
        if cover_url:
            params["cover_url"] = cover_url
        elif thumb_offset is not None:
            params["thumb_offset"] = str(thumb_offset)
    elif kind == "story":
        params = {"media_type": "STORIES", ("video_url" if is_video(media[0]) else "image_url"): media[0]}
    elif kind == "carousel":
        if not 2 <= len(media) <= 20:
            sys.exit("カルーセルは2〜20枚です。")
        children = []
        for i, u in enumerate(media, 1):
            child = {"is_carousel_item": "true"}
            if is_video(u):
                child.update({"media_type": "VIDEO", "video_url": u})
            else:
                child["image_url"] = u
            r = ig.post(f"{uid}/media", child, go)
            cid = (r or {}).get("id", f"<子{i}のID>")
            if is_video(u):
                wait_finished(cid, go)
            children.append(cid)
        params = {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption}
    else:
        sys.exit(f"--kind が分かりません: {kind}")

    r = ig.post(f"{uid}/media", params, go)
    container = (r or {}).get("id", "<入れ物のID>")
    wait_finished(container, go)
    r = ig.post(f"{uid}/media_publish", {"creation_id": container}, go)
    if not go:
        print("\n（dry-run でした。本当に投稿するときは --go を付けます）")
        return None
    media_id = r.get("id")
    link = ig.get(media_id, {"fields": "permalink,timestamp"}, go) or {}
    append_log("published.jsonl", {"media_id": media_id, "kind": kind, "permalink": link.get("permalink"),
                                   "timestamp": link.get("timestamp"), "caption_head": caption[:40]})
    print(f"投稿しました: {link.get('permalink')}  (media_id={media_id})")
    return media_id


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--kind", required=True, choices=["image", "carousel", "reel", "story"])
    p.add_argument("--media", action="append", required=True, help="公開URL（カルーセルは複数回）")
    p.add_argument("--caption")
    p.add_argument("--caption-file", help="drafts の md（## キャプション の中だけ使う）")
    p.add_argument("--cover-url", help="リールの表紙画像のURL")
    p.add_argument("--thumb-offset", type=int, help="表紙にする位置（ミリ秒）")
    p.add_argument("--no-feed", action="store_true", help="リールをフィードに出さない")
    p.add_argument("--alt-text")
    p.add_argument("--go", action="store_true", help="本当に投稿する")
    a = p.parse_args()
    cap = caption_of(read_text_arg(None, a.caption_file)) if a.caption_file else (a.caption or "")
    publish(a.kind, a.media, cap, a.go, a.cover_url, not a.no_feed, a.alt_text, a.thumb_offset)


if __name__ == "__main__":
    main()
