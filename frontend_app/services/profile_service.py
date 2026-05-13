import json
import re
import sys
import uuid
from datetime import date, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any
from services.comment_preprocess import preprocess_payload
from services.session_alerts import notify_session_expired

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = PROJECT_ROOT / "Profile Scraper"
PROFILE_SCRIPT = PROFILE_ROOT / "src" / "instagram_scraper" / "profile_scraper.py"
LEADERS_FILE = PROFILE_ROOT / "config" / "leaders.json"
OUTPUT_DIR = PROFILE_ROOT / "data" / "instagram_data"


def _load_module_from_path(path: Path, module_name: str):
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from: {path}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _normalize_timeline(value: int, unit: str) -> str:
    unit_map = {
        "hours": "h",
        "days": "d",
        "weeks": "w",
        "months": "m",
    }
    suffix = unit_map[unit]
    return f"{value}{suffix}"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", text).strip("_").lower() or "profile"


def run_profile_scraper(
    profile_urls: list[str],
    timeline_value: int | None,
    timeline_unit: str | None,
    filter_mode: str = "Relative",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    clean_urls = [u.strip() for u in profile_urls if u.strip()]
    clean_urls = [u for u in clean_urls if u.startswith("http")]
    if not clean_urls:
        raise ValueError("Please provide at least one valid profile URL starting with http:// or https://")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timeline = _normalize_timeline(timeline_value, timeline_unit) if timeline_value and timeline_unit else "all"
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    label_key = f"ui_{uuid.uuid4().hex[:8]}"
    slug = _slugify(clean_urls[0].split("instagram.com/")[-1].strip("/"))
    output_path = OUTPUT_DIR / f"{slug}_{now_str}.json"

    with open(LEADERS_FILE, "r", encoding="utf-8") as f:
        original_leaders = json.load(f)

    updated_leaders = dict(original_leaders)
    updated_leaders[label_key] = clean_urls

    try:
        with open(LEADERS_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_leaders, f, indent=2, ensure_ascii=False)

        module_name = f"profile_scraper_ui_{uuid.uuid4().hex}"
        scraper_module = _load_module_from_path(PROFILE_SCRIPT, module_name)
        if not scraper_module.validate_instagram_session():
            notify_session_expired(
                scraper_name="Profile Scraper",
                context_text="Session check failed before profile scrape.",
            )
            raise RuntimeError(
                "Instagram session expired. Please contact admin to refresh authentication cookies."
            )
        kwargs = {
            "leader_name": label_key,
            "output_path": str(output_path),
        }
        if filter_mode == "Custom Date Range" and start_date and end_date:
            kwargs["start_date"] = start_date.strftime("%Y-%m-%d")
            kwargs["end_date"] = end_date.strftime("%Y-%m-%d")
            kwargs["tf_input"] = "all"
        else:
            kwargs["tf_input"] = timeline

        scraper_module.run_unified_scraper(**kwargs)
    finally:
        with open(LEADERS_FILE, "w", encoding="utf-8") as f:
            json.dump(original_leaders, f, indent=2, ensure_ascii=False)

    if not output_path.exists():
        raise RuntimeError("Profile scraper did not create a JSON output file.")

    with open(output_path, "r", encoding="utf-8") as f:
        raw_result = json.load(f)

    return preprocess_payload(raw_result, str(output_path), PROFILE_ROOT)
