#!/usr/bin/env python3
"""
Validation script for the Pastebin Keyword Crawler

This script analyzes the results in keyword_matches.jsonl and provides
a summary of the findings.
"""

import json
import os
import sys
from collections import Counter

def validate_results(file_path="keyword_matches.jsonl"):
    """Validate and summarize the results from the crawler"""
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return False
    
    # Check if file is empty
    if os.path.getsize(file_path) == 0:
        print(f"Warning: {file_path} is empty. No matches were found.")
        return False
    
    matches = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    match = json.loads(line.strip())
                    matches.append(match)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return False
    
    if not matches:
        print("No valid matches found in the file.")
        return False
    
    # Count total matches
    print(f"Total matches found: {len(matches)}")
    
    # Count unique paste IDs
    unique_ids = set(match['paste_id'] for match in matches)
    print(f"Unique paste IDs: {len(unique_ids)}")
    
    # Analyze keywords found
    all_keywords = []
    for match in matches:
        all_keywords.extend(match['keywords_found'])
    
    keyword_counts = Counter(all_keywords)
    print("\nKeyword frequency:")
    for keyword, count in keyword_counts.most_common():
        print(f"  {keyword}: {count}")
    
    # Check for Telegram and crypto combinations
    telegram_and_crypto = 0
    for match in matches:
        has_telegram = any(kw in ["t.me", "telegram.me", "telegram"] for kw in match['keywords_found'])
        has_crypto = any(kw not in ["t.me", "telegram.me", "telegram"] for kw in match['keywords_found'])
        
        if has_telegram and has_crypto:
            telegram_and_crypto += 1
    
    print(f"\nPastes with both Telegram links and crypto terms: {telegram_and_crypto}")
    
    return True

if __name__ == "__main__":
    file_path = "keyword_matches.jsonl"
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    print(f"Validating results in {file_path}...")
    if validate_results(file_path):
        print("\nValidation completed successfully.")
    else:
        print("\nValidation failed or found issues with the results.") 