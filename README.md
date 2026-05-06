# Instagram Scraper Projects

This repository contains two separate Instagram scraping projects under one umbrella:

1. **Profile Scraper**: Scrapes entire Instagram profiles, including posts, followers, and comments.
2. **Links Scraper**: Scrapes individual posts from a list of URLs provided in .txt files.

Both projects share a common virtual environment (`.venv`) and secrets (e.g., cookies) for consistency.

## Project Structure

- `Profile Scraper/`: For scraping full profiles.
- `Links Scraper/`: For scraping posts from links.
- `.venv/`: Shared Python environment.
- `secrets/`: Shared cookies and sensitive data.

## Setup

1. Activate the shared virtual environment:
   ```bash
   .\.venv\Scripts\Activate.ps1
   ```

2. Generate cookies (shared):
   - Run from either project: `python src/instagram_scraper/generate_cookies.py`
   - Saves to `secrets/cookies.pkl`.

3. Navigate to the desired project and follow its README.

## ⚠️ Disclaimer
These tools are for educational purposes only. Always comply with Instagram's Terms of Service and use responsibly to avoid account suspension.
