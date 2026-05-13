import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = PROJECT_ROOT / "frontend_app" / ".session_alert_state.json"


def _read_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def _cooldown_ok(key: str, cooldown_seconds: int) -> bool:
    state = _read_state()
    last = float(state.get(key, 0.0))
    now = datetime.now(timezone.utc).timestamp()
    if now - last < cooldown_seconds:
        return False
    state[key] = now
    _write_state(state)
    return True


def notify_session_expired(scraper_name: str, context_text: str = "") -> bool:
    """
    Sends admin email alert if SMTP settings exist.
    Returns True when email send is attempted and succeeds, otherwise False.
    """
    cooldown_seconds = int(os.getenv("IG_SESSION_ALERT_COOLDOWN_SECONDS", "1800"))
    if not _cooldown_ok(f"expired:{scraper_name}", cooldown_seconds):
        return False

    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    recipients_raw = os.getenv("SMTP_TO", "").strip()

    if not host or not sender or not recipients_raw:
        return False

    recipients = [x.strip() for x in recipients_raw.split(",") if x.strip()]
    if not recipients:
        return False

    subject = f"[ALERT] Instagram Session Expired - {scraper_name}"
    now_ist = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = (
        "Instagram scraper session appears expired.\n\n"
        f"Scraper: {scraper_name}\n"
        f"Time: {now_ist}\n"
        f"Context: {context_text or 'N/A'}\n\n"
        "Action required:\n"
        "1) Regenerate cookies via generate_cookies.py\n"
        "2) Replace secrets/cookies.pkl on deployed server\n"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            try:
                smtp.starttls()
                smtp.ehlo()
            except Exception:
                pass
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)
        return True
    except Exception:
        return False

