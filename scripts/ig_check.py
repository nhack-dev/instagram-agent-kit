"""投稿の前に文面を機械で確かめる（API は呼ばない）。

  python3 scripts/ig_check.py drafts/2026-11-01-reel.md

確かめること（公式の上限）：キャプション2200字・ハッシュタグ30個・@タグ20個。
加えて、この型の決まり（AGENT.md）：ハッシュタグは3〜8個／1行目は28字以内／URLを本文に書かない。
"""

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401

import argparse
import re
import sys
from pathlib import Path

LIMIT_CHARS, LIMIT_TAGS, LIMIT_MENTIONS = 2200, 30, 20


def check(text: str) -> list[str]:
    errs, warns = [], []
    tags = re.findall(r"#[^\s#]+", text)
    mentions = re.findall(r"(?<![\w.])@[A-Za-z0-9_.]+", text)
    if len(text) > LIMIT_CHARS:
        errs.append(f"キャプションが {len(text)} 字（上限 {LIMIT_CHARS}）")
    if len(tags) > LIMIT_TAGS:
        errs.append(f"ハッシュタグが {len(tags)} 個（上限 {LIMIT_TAGS}）")
    if len(mentions) > LIMIT_MENTIONS:
        errs.append(f"@タグが {len(mentions)} 個（上限 {LIMIT_MENTIONS}）")
    if not 3 <= len(tags) <= 8:
        warns.append(f"ハッシュタグ {len(tags)} 個（このキットの目安は3〜8個）")
    first = text.splitlines()[0] if text else ""
    if len(first) > 28:
        warns.append(f"1行目が {len(first)} 字（目安28字以内・フィードで切れる）")
    if re.search(r"https?://", text):
        warns.append("本文にURLがあります（キャプションのURLは押せません。プロフィールへ）")
    return [f"NG: {e}" for e in errs] + [f"注意: {w}" for w in warns]


def caption_of(md: str) -> str:
    """drafts の md から「## キャプション」の中だけを取り出す（無ければ全文）。"""
    m = re.search(r"^## キャプション\s*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return (m.group(1) if m else md).strip()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("file")
    a = p.parse_args()
    cap = caption_of(Path(a.file).read_text(encoding="utf-8"))
    out = check(cap)
    n_tags = len(re.findall(r"#[^\s#]+", cap))
    print(f"{len(cap)} 字 ／ ハッシュタグ {n_tags} 個")
    for line in out:
        print(line)
    sys.exit(1 if any(x.startswith("NG") for x in out) else 0)
