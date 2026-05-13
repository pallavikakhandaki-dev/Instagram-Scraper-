import json
from typing import Any


def format_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)
