import json
import pandas as pd
import os
import glob

# ====== CONFIGURATION ======
# You can specify a file path here or leave it empty to automatically find the latest JSON
json_path = os.path.join("..", "..", "data", "instagram_data", "ashok_kharat", "ashok_kharat_20260506_110153.json")
output_excel = os.path.join("..", "..", "data", "excel_data", "output.xlsx")

# If the hardcoded path above doesn't exist, try to find the latest JSON in the folder
if not os.path.exists(json_path):
    print(f"File {json_path} not found. Searching for latest JSON...")
    search_dir = os.path.join("..", "..", "data", "instagram_data")
    search_pattern = os.path.join(search_dir, "**", "*.json")
    files = glob.glob(search_pattern, recursive=True)
    if files:
        json_path = max(files, key=os.path.getmtime)
        print(f"Using latest file found: {json_path}")
    else:
        print("No JSON files found in the directory!")
        exit(1)

# ====== LOAD JSON ======
print(f"Loading data from: {json_path}")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

rows = []

# ====== EXTRACT POSTS ======
# Support both top-level "posts" and nested "profiles" structure
posts = data.get("posts", [])
if not posts and "profiles" in data:
    for profile in data.get("profiles", []):
        posts.extend(profile.get("posts", []))

print(f"Found {len(posts)} posts. Processing comments...")

# ====== PROCESS POSTS ======
for post in posts:
    post_url = post.get("post_url", "")
    caption = post.get("caption", "")
    likes_count = post.get("likes_count", "")
    comments_count = post.get("comments_count", "")
    timestamp = post.get("timestamp", "")
    
    # Extract comments list
    comments_list = post.get("comments", [])
    
    for comment_obj in comments_list:
        raw_comment = comment_obj.get("comment_text", "")
        
        if not raw_comment:
            continue

        # Split multiple comments using "\nReply" (specific to this scraper's format)
        split_comments = raw_comment.split("\nReply")
        
        for c in split_comments:
            clean_comment = c.strip()
            
            # Skip empty / noise placeholders
            if not clean_comment or "No comments yet" in clean_comment or "Start the conversation" in clean_comment:
                continue
            
            # Additional cleanup for noise like "View all X replies"
            if "View all" in clean_comment and "replies" in clean_comment:
                continue

            rows.append({
                "post_url": post_url,
                "caption": caption,
                "likes_count": likes_count,
                "comments_count": comments_count,
                "timestamp": timestamp,
                "comments": clean_comment
            })

# ====== CREATE DATAFRAME ======
if not rows:
    print("Warning: No comments were extracted!")
    df = pd.DataFrame(columns=["post_url", "caption", "likes_count", "comments_count", "timestamp", "comments"])
else:
    df = pd.DataFrame(rows)
    print(f"Successfully extracted {len(rows)} comment rows.")

# ====== SAVE TO EXCEL ======
try:
    df.to_excel(output_excel, index=False)
    # Using ASCII friendly success message to avoid encoding errors
    print(f"DONE: Excel created successfully -> {output_excel}")
except Exception as e:
    print(f"Error saving Excel: {e}")
