import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def _is_meta_line(line: str) -> bool:
    text = line.strip().lower()
    if not text:
        return True
    if text in {"reply", "see translation"}:
        return True
    if re.fullmatch(r"\d+\s*(like|likes)", text):
        return True
    if re.fullmatch(r"(view all\s+\d+\s+replies|view replies)", text):
        return True
    if re.fullmatch(r"\d+\s*(s|m|h|d|w)", text):
        return True
    if "comments from facebook" in text:
        return True
    return False


def _looks_like_username(line: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9._]{2,40}", line.strip()))


def _clean_caption(caption: str) -> str:
    lines = [x.strip() for x in (caption or "").splitlines() if x.strip()]
    if lines and _looks_like_username(lines[0]):
        lines = lines[1:]
    if lines and re.fullmatch(r"\d+\s*(s|m|h|d|w)", lines[0].lower()):
        lines = lines[1:]
    return "\n".join(lines).strip()


def _get_posts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("posts"):
        return payload["posts"]
    out: list[dict[str, Any]] = []
    for profile in payload.get("profiles", []):
        out.extend(profile.get("posts", []))
    return out


def preprocess_payload(payload: dict[str, Any], source_file: str, output_root: Path) -> dict[str, Any]:
    posts = _get_posts(payload)
    rows: list[dict[str, Any]] = []

    for post in posts:
        post_url = post.get("post_url", "")
        caption = _clean_caption(post.get("caption", ""))
        timestamp = post.get("timestamp", "")
        likes_count = post.get("likes_count", "")
        comments_count = post.get("comments_count", "")

        comment_objs = post.get("comments", [])
        if not comment_objs:
            continue
        raw_text = (comment_objs[0] or {}).get("comment_text", "")
        lines = [x.strip() for x in (raw_text or "").splitlines() if x.strip()]
        cap_lines = [x.strip() for x in caption.splitlines() if x.strip()]
        if cap_lines and len(lines) >= len(cap_lines) and lines[: len(cap_lines)] == cap_lines:
            lines = lines[len(cap_lines) :]
        lines = [ln for ln in lines if not _is_meta_line(ln)]

        current_user = ""
        buff: list[str] = []
        post_rows: list[dict[str, Any]] = []

        def flush():
            if not buff:
                return
            txt = " ".join(buff).strip()
            if not txt:
                return
            post_rows.append(
                {
                    "post_url": post_url,
                    "caption": caption,
                    "post_timestamp": timestamp,
                    "post_likes_count": likes_count,
                    "post_comments_count": comments_count,
                    "comment_username": current_user,
                    "comment_text": txt,
                }
            )

        for ln in lines:
            if _looks_like_username(ln):
                flush()
                current_user = ln
                buff = []
            else:
                buff.append(ln)
        flush()

        # The first parsed block in current scraper output is usually the post caption.
        # Always drop it so only actual user comments remain.
        if post_rows:
            post_rows = post_rows[1:]
        rows.extend(post_rows)

    out_json_dir = output_root / "data" / "processed_json"
    out_excel_dir = output_root / "data" / "processed_excel"
    out_json_dir.mkdir(parents=True, exist_ok=True)
    out_excel_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = Path(source_file).stem
    out_json = out_json_dir / f"{base}_comments_clean_{ts}.json"
    out_excel = out_excel_dir / f"{base}_comments_clean_{ts}.xlsx"

    processed_payload = {
        "source_file": source_file,
        "total_posts": len(posts),
        "total_comments_rows": len(rows),
        "comments": rows,
    }

    out_json.write_text(json.dumps(processed_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_excel(out_excel, index=False)

    return {
        "raw_scrape": payload,
        "processed_comments": processed_payload,
        "processed_json_path": str(out_json),
        "processed_excel_path": str(out_excel),
    }
