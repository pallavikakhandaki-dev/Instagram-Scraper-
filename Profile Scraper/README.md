# Profile Scraper

A robust, Selenium-based Instagram scraper designed to extract profile statistics, post metadata, and detailed comments for targeted accounts. This tool uses session cookies to bypass login challenges and supports timeframe-based filtering for efficient data collection.

## 🚀 Features

- **Profile Extraction**: Captures username, bio, follower count, and total posts.
- **Post Metadata**: Extracts captions, like counts, and precise timestamps.
- **Deep Comment Scraping**: Automatically scrolls and expands all comments for thorough data gathering.
- **Timeframe Filtering**: Scrape posts within a specific window (e.g., `7d`, `1m`, `all`).
- **Real-time JSON Output**: Saves data incrementally to prevent loss during long runs.
- **Headless Support**: Runs in the background using Chrome's headless mode.

## 📋 Prerequisites

- **Python 3.8+**
- **Google Chrome Browser**
- **ChromeDriver** (Managed automatically by `webdriver-manager`)

## 🛠️ Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate Session Cookies**:
   To avoid being blocked by Instagram's login wall, run the following script to create a `cookies.pkl` file:
   ```bash
   python src/instagram_scraper/generate_cookies.py
   ```
   *Follow the on-screen instructions to manually log in within the 60-second window.*

3. **Configure Targets**:
   Edit `config/leaders.json` to include the Instagram profile URLs you wish to scrape:
   ```json
   {
       "Leader Name": [
           "https://www.instagram.com/profile1/",
           "https://www.instagram.com/profile2/"
       ]
   }
   ```

## 📂 Usage

Run the main scraper script:
```bash
python src/instagram_scraper/profile_scraper.py
```

### Prompt Instructions:
1. **Enter leader name**: Type the name exactly as it appears in `leaders.json`.
2. **Selection (Timeframe)**: Enter the desired timeframe:
   - `7d` for the last 7 days
   - `1m` for the last month
   - `all` for all available posts

## 📊 Data Output

All scraped data is saved as JSON files in the `data/instagram_data/` directory. Each file is named using the pattern:
`leader_name_YYYYMMDD_HHMMSS.json`

### Data Structure:
```json
{
    "leader_name": "...",
    "scrape_timestamp": "...",
    "profiles": [
        {
            "account": {
                "username": "...",
                "bio": "...",
                "followers": "...",
                "posts_count": "..."
            },
            "posts": [
                {
                    "post_url": "...",
                    "caption": "...",
                    "likes_count": "...",
                    "timestamp": "...",
                    "comments": [
                        { "comment_text": "..." }
                    ]
                }
            ]
        }
    ]
}
```

## ⚠️ Disclaimer
This tool is for educational purposes only. Always comply with Instagram's Terms of Service and use responsibly to avoid account suspension.
