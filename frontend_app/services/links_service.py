import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from services.comment_preprocess import preprocess_payload
from importlib.util import module_from_spec, spec_from_file_location
from services.session_alerts import notify_session_expired

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LINKS_ROOT = PROJECT_ROOT / "Links Scraper"
SCRIPT_PATH = LINKS_ROOT / "src" / "instagram_scraper" / "scrape_from_links.py"
HTML_FILES_DIR = LINKS_ROOT / "html_files"
OUTPUT_DIR = LINKS_ROOT / "data" / "instagram_data"
PROFILE_SCRIPT = PROJECT_ROOT / "Profile Scraper" / "src" / "instagram_scraper" / "profile_scraper.py"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", text).strip("_").lower() or "links"


def _latest_json_in_label_dir(label: str) -> Path:
    label_dir = OUTPUT_DIR / _slugify(label)
    if not label_dir.exists():
        raise RuntimeError("No output folder found for this label.")
    json_files = sorted(label_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not json_files:
        raise RuntimeError("No JSON output found for this label.")
    return json_files[0]


def _load_module_from_path(path: Path, module_name: str):
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from: {path}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_links_scraper(links_text: str, label: str) -> dict[str, Any]:
    lines = [line.strip() for line in links_text.splitlines() if line.strip()]
    urls = [line for line in lines if line.startswith("http")]
    if not urls:
        raise ValueError("Please provide at least one valid URL starting with http:// or https://")

    profile_module = _load_module_from_path(PROFILE_SCRIPT, f"profile_scraper_session_check_{datetime.now().timestamp()}")
    if not profile_module.validate_instagram_session():
        notify_session_expired(
            scraper_name="Links Scraper",
            context_text="Session check failed before links scrape.",
        )
        raise RuntimeError(
            "Instagram session expired. Please contact admin to refresh authentication cookies."
        )

    HTML_FILES_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file_name = f"ui_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    tmp_file_path = HTML_FILES_DIR / tmp_file_name
    tmp_file_path.write_text("\n".join(urls), encoding="utf-8")

    try:
        cmd = [sys.executable, str(SCRIPT_PATH), tmp_file_name, label.strip() or "ui_links"]
        completed = subprocess.run(
            cmd,
            cwd=str(SCRIPT_PATH.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Links scraper failed.\n"
                f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}"
            )

        output_json = _latest_json_in_label_dir(label.strip() or "ui_links")
        with open(output_json, "r", encoding="utf-8") as f:
            raw_result = json.load(f)
        return preprocess_payload(raw_result, str(output_json), LINKS_ROOT)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()
