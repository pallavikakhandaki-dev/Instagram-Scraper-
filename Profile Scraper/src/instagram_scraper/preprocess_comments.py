import glob
import json
import os
import re
from datetime import datetime

import pandas as pd


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "instagram_data")
OUTPUT_JSON_DIR = os.path.join(PROJECT_ROOT, "data", "processed_json")
OUTPUT_EXCEL_DIR = os.path.join(PROJECT_ROOT, "data", "processed_excel")


def latest_json_file():
    files = glob.glob(os.path.join(INPUT_DIR, "**", "*.json"), recursive=True)
    if not files:
        raise FileNotFoundError(f"No JSON files found in: {INPUT_DIR}")
    return max(files, key=os.path.getmtime)


def get_posts(payload):
    posts = payload.get("posts", [])
    if posts:
        return posts
    collected = []
    for profile in payload.get("profiles", []):
        collected.extend(profile.get("posts", []))
    return collected


def is_meta_line(line):
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


def looks_like_username(line):
    text = line.strip()
    return bool(re.fullmatch(r"[a-zA-Z0-9._]{2,40}", text))


def clean_caption_text(caption):
    lines = [x.strip() for x in (caption or "").splitlines() if x.strip()]
    if not lines:
        return ""

    # Common Instagram prefix in scraped caption: username + relative time.
    if lines and looks_like_username(lines[0]):
        lines = lines[1:]
    if lines and re.fullmatch(r"\d+\s*(s|m|h|d|w)", lines[0].lower()):
        lines = lines[1:]

    return "\n".join(lines).strip()


def clean_comment_block(raw_text, caption):
    lines = [x.strip() for x in raw_text.splitlines() if x.strip()]
    cap_lines = [x.strip() for x in (caption or "").splitlines() if x.strip()]

    # Drop the caption block if it appears at the top of comments.
    if cap_lines and len(lines) >= len(cap_lines):
        if lines[: len(cap_lines)] == cap_lines:
            lines = lines[len(cap_lines) :]

    cleaned = []
    for line in lines:
        if is_meta_line(line):
            continue
        cleaned.append(line)
    return cleaned


def extract_comments_for_post(post):
    post_url = post.get("post_url", "")
    caption = clean_caption_text(post.get("caption", ""))
    timestamp = post.get("timestamp", "")
    likes_count = post.get("likes_count", "")
    comments_count = post.get("comments_count", "")

    comment_objs = post.get("comments", [])
    if not comment_objs:
        return []

    raw_text = comment_objs[0].get("comment_text", "")
    lines = clean_comment_block(raw_text, caption)
    if not lines:
        return []

    rows = []
    current_user = ""
    buffer = []

    def flush_comment():
        if not buffer:
            return
        text = " ".join(buffer).strip()
        if not text:
            return
        rows.append(
            {
                "post_url": post_url,
                "caption": caption,
                "post_timestamp": timestamp,
                "post_likes_count": likes_count,
                "post_comments_count": comments_count,
                "comment_username": current_user,
                "comment_text": text,
            }
        )

    for line in lines:
        if looks_like_username(line):
            flush_comment()
            current_user = line
            buffer = []
            continue
        buffer.append(line)

    flush_comment()
    return rows


def preprocess_file(input_path):
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
    os.makedirs(OUTPUT_EXCEL_DIR, exist_ok=True)

    if not input_path:
        input_path = latest_json_file()
    input_path = os.path.abspath(input_path)

    with open(input_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    posts = get_posts(payload)
    all_rows = []
    for post in posts:
        all_rows.extend(extract_comments_for_post(post))

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(input_path))[0]
    out_json = os.path.join(OUTPUT_JSON_DIR, f"{base}_comments_clean_{now}.json")
    out_excel = os.path.join(OUTPUT_EXCEL_DIR, f"{base}_comments_clean_{now}.xlsx")

    output_payload = {
        "source_file": input_path,
        "total_posts": len(posts),
        "total_comments_rows": len(all_rows),
        "comments": all_rows,
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    df = pd.DataFrame(all_rows)
    df.to_excel(out_excel, index=False)

    return {
        "source_file": input_path,
        "posts_processed": len(posts),
        "comment_rows_extracted": len(all_rows),
        "clean_json_path": out_json,
        "clean_excel_path": out_excel,
        "clean_payload": output_payload,
    }


def main():
    result = preprocess_file(None)
    print(f"Input JSON: {result['source_file']}")
    print(f"Posts processed: {result['posts_processed']}")
    print(f"Comment rows extracted: {result['comment_rows_extracted']}")
    print(f"Clean JSON: {result['clean_json_path']}")
    print(f"Clean Excel: {result['clean_excel_path']}")


if __name__ == "__main__":
    main()
