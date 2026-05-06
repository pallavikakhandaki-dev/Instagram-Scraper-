## 🔧 Working Principles

### Profile Scraper Workflow

1. **Initialization**:
   - Reads profile URLs from `config/leaders.json`
   - Loads saved cookies from `secrets/cookies.pkl` to maintain session

2. **Profile Data Collection**:
   - Navigates to each Instagram profile URL
   - Extracts profile metadata: username, bio, follower count, post count
   - Identifies all posts on the profile

3. **Post Processing**:
   - Scrapes individual post metadata: caption, likes, timestamp
   - Automatically scrolls and loads comments (including "load more" interactions)
   - Extracts all comment text and metadata

4. **Data Storage**:
   - Saves incrementally to JSON after each post (prevents data loss on interruption)
   - Final JSON structure includes profile info and all associated posts/comments
   - Outputs saved to `data/instagram_data/<profile_name>_<timestamp>.json`
   - Exports to Excel at completion: `data/excel_data/<profile_name>_<timestamp>.xlsx`

5. **Timeframe Filtering**:
   - Optional: Filter posts by timeframe (7 days, 1 month, or all)
   - Only scrapes posts within the selected window

### Links Scraper Workflow

1. **Input Setup**:
   - Reads a `.txt` file containing Instagram post URLs from `html_files/`
   - One URL per line (supports direct links, reels, and posts)
   - Normalizes URLs to standard `/p/` format

2. **Cookie & Session Management**:
   - Loads saved cookies from `secrets/cookies.pkl` for authentication
   - Bypasses login screens by using existing session

3. **Post Scraping**:
   - Iterates through each URL in the file
   - Extracts post metadata: caption, likes count, comments count, timestamp
   - Automatically scrolls comment section and clicks "load more" buttons
   - Collects all comment text from the post

4. **Comment Extraction**:
   - Finds the scrollable comment container on each post
   - Loads additional comments dynamically
   - Combines all comment text into a single field per post
   - Filters out meta-comments (e.g., "Reply", "View replies")

5. **Data Persistence**:
   - Incremental JSON saves after each post (prevents data loss)
   - Creates subdirectory based on label: `data/instagram_data/<label>/`
   - Saves JSON: `data/instagram_data/<label>/<label>_<timestamp>.json`
   - Exports to Excel: `data/excel_data/<label>_<timestamp>.xlsx`

6. **Post-Processing**:
   - Use `json_to_excel_new.py` to convert saved JSON to formatted Excel
   - Automatically finds latest JSON if not specified

## 🔄 Data Flow Diagram

```
Profile Scraper:
  leaders.json → generate_cookies.py → profile_scraper.py → JSON → json_to_excel_new.py → Excel

Links Scraper:
  html_files/*.txt → generate_cookies.py → scrape_from_links.py → JSON → json_to_excel_new.py → Excel

Shared:
  secrets/cookies.pkl (shared across both projects)
  .venv (shared Python environment)
```

## 🛡️ Key Features

- **Session Persistence**: Uses saved cookies to maintain authentication
- **Incremental Saving**: JSON saved after each post to prevent data loss
- **Comment Loading**: Automatically loads all comments by scrolling and clicking
- **Error Handling**: Graceful handling of network errors and permission issues
- **Duplicate Prevention**: Skips duplicate URLs/posts
- **Flexible Path Handling**: Works from any directory structure
- **Data Normalization**: Converts different URL formats to standard Instagram URLs
- **Excel Export**: Automatic conversion from JSON to formatted Excel spreadsheets

## 📊 Output Data Structure

### JSON Format (Profile & Links Scraper)
```json
{
  "label": "Profile/Label Name",
  "scraped_at": "20260506_110153",
  "total_posts_found": 25,
  "posts_scraped_so_far": 25,
  "posts": [
    {
      "post_url": "https://www.instagram.com/p/...",
      "caption": "Post caption text...",
      "likes_count": "1,234",
      "comments_count": "56",
      "timestamp": "2026-05-05T12:00:00Z",
      "comments": [
        { "comment_text": "Comment 1\nComment 2\n..." }
      ]
    }
  ]
}
```

### Excel Export Format
| Column | Description |
|--------|-------------|
| Post URL | Direct link to the Instagram post |
| Caption | Full caption text |
| Likes | Total likes count |
| Comments Count | Total number of comments |
| Timestamp | Post creation timestamp |
| Comments Text | All comment text combined |

## ⚙️ Environment & Dependencies

- **Python**: 3.8+
- **Selenium**: Browser automation for Instagram scraping
- **Pandas**: Data handling and Excel export
- **webdriver-manager**: Automatic ChromeDriver management
- **Chrome Browser**: Required for Selenium automation

## � How to Run - Step by Step

### Prerequisites & Initial Setup

1. **Clone/Setup the Repository**:
   ```bash
   git clone <repository-url>
   cd "Instagram Scraper"
   ```

2. **Activate the Virtual Environment**:
   ```bash
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   
   # Windows (Command Prompt)
   .venv\Scripts\activate.bat
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install Dependencies** (if not already installed):
   ```bash
   pip install -r Profile\ Scraper/requirements.txt
   ```

4. **Generate Instagram Session Cookies** (One-time setup):
   ```bash
   # From root directory, navigate to either project
   cd "Profile Scraper"
   
   # Run the cookie generation script
   python src/instagram_scraper/generate_cookies.py
   
   # A browser will open. Log in to your Instagram account manually.
   # You have 60 seconds to complete the login.
   # Cookies will be saved to: ../../../secrets/cookies.pkl
   ```

### Running Profile Scraper

1. **Configure Target Profiles**:
   ```bash
   # Edit Profile Scraper/config/leaders.json
   # Add Instagram profile URLs you want to scrape
   ```
   
   Example `leaders.json`:
   ```json
   {
     "Leader Name": [
       "https://www.instagram.com/username1/",
       "https://www.instagram.com/username2/"
     ]
   }
   ```

2. **Run the Scraper**:
   ```bash
   cd "Profile Scraper"
   python src/instagram_scraper/profile_scraper.py
   ```

3. **Follow Prompts**:
   - Enter the leader name (exactly as in `leaders.json`)
   - Select timeframe: `7d`, `1m`, or `all`
   - Script will scrape all posts and comments

4. **Find Output**:
   - JSON: `Profile Scraper/data/instagram_data/<leader_name>_<timestamp>.json`
   - Excel: `Profile Scraper/data/excel_data/<leader_name>_<timestamp>.xlsx`

### Running Links Scraper

1. **Prepare URLs File**:
   ```bash
   # Create or edit a .txt file in: Links Scraper/html_files/
   # Add one Instagram post URL per line
   ```
   
   Example `ashok_kharat.txt`:
   ```
   https://www.instagram.com/p/ABC123/
   https://www.instagram.com/reel/DEF456/
   https://www.instagram.com/p/GHI789/
   ```

2. **Run the Scraper**:
   ```bash
   cd "Links Scraper"
   python src/instagram_scraper/scrape_from_links.py
   ```

3. **Select Input File**:
   - Script will list all `.txt` files in `html_files/`
   - Enter the file number or name
   - Enter a label for the scrape (e.g., "Ashok Kharat")

4. **Find Output**:
   - JSON: `Links Scraper/data/instagram_data/<label>/<label>_<timestamp>.json`
   - Excel: `Links Scraper/data/excel_data/<label>_<timestamp>.xlsx`

### Converting JSON to Excel

1. **From Profile Scraper**:
   ```bash
   cd "Profile Scraper"
   python src/instagram_scraper/json_to_excel_new.py
   ```

2. **From Links Scraper**:
   ```bash
   cd "Links Scraper"
   python src/instagram_scraper/json_to_excel_new.py
   ```

3. **Script Behavior**:
   - Looks for the latest JSON file if specific one not found
   - Processes comments and extracts structured data
   - Saves to `data/excel_data/output.xlsx`

### Troubleshooting

- **No cookies file found**: Run `generate_cookies.py` first to create `secrets/cookies.pkl`
- **No `.txt` files found in Links Scraper**: Create files in `Links Scraper/html_files/`
- **"Permission denied" errors**: Ensure the data folder exists and has write permissions
- **SSL certificate errors**: Usually fixed by the script's built-in environment variable handling

## �🚀 Running the Projects

### Profile Scraper
```bash
cd "Profile Scraper"
python src/instagram_scraper/profile_scraper.py
```

### Links Scraper
```bash
cd "Links Scraper"
python src/instagram_scraper/scrape_from_links.py
```

### Convert JSON to Excel
From either project:
```bash
python src/instagram_scraper/json_to_excel_new.py
```

## ⚠️ Disclaimer
These tools are for educational purposes only. Always comply with Instagram's Terms of Service and use responsibly to avoid account suspension.
