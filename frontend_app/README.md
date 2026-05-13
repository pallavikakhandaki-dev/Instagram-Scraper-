# Instagram Scraper Frontend UI

This frontend is a separate UI layer for your existing backend scripts.
No backend files were modified.

## What it does

- Profile Scraper UI:
  - Input: Instagram profile URL
  - Input: timeline as value + unit (`hours`, `days`, `weeks`, `months`)
  - Output: backend JSON shown in formatted view + table + download button

- Links Scraper UI:
  - Input: multiple Instagram links (one per line)
  - Input: label
  - Output: backend JSON shown in formatted view + table + download button

## Run

From repository root:

```powershell
pip install -r frontend_app/requirements.txt
streamlit run frontend_app/app.py
```

## Notes

- Backend code inside `Profile Scraper` and `Links Scraper` is not edited.
- The Profile UI temporarily adds a generated key to `Profile Scraper/config/leaders.json` for one run and restores the original file immediately after execution.
- Links UI creates a temporary `.txt` inside `Links Scraper/html_files/` and removes it after run.
