#!/usr/bin/env python3
"""
Pastebin Keyword Crawler

This script scrapes Pastebin's public archive for pastes containing 
crypto-related keywords or Telegram links, and saves them to a JSONL file.
"""

import os
import re
import json
import time
import random
import logging
import datetime
import requests
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from dateutil.parser import parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
ARCHIVE_URL = "https://pastebin.com/archive"
RAW_URL_TEMPLATE = "https://pastebin.com/raw/{}"
OUTPUT_FILE = "keyword_matches.jsonl"
MIN_DELAY = 2
MAX_DELAY = 5

# Keywords to search for
CRYPTO_KEYWORDS = [
    "crypto", "bitcoin", "btc", "ethereum", "eth", "blockchain", 
    "binance", "coinbase", "wallet", "nft", "token", "altcoin",
    "defi", "mining", "staking", "ledger", "metamask", "dogecoin",
    "ripple", "xrp", "solana", "cardano", "ada"
]
TELEGRAM_KEYWORDS = ["t.me", "telegram.me", "telegram"]

class PastebinCrawler:
    """Crawler for extracting and analyzing Pastebin content based on keywords"""
    
    def __init__(self, use_threading=False, max_workers=5):
        """Initialize the crawler with default settings"""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Create output file if it doesn't exist
        if not os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'w') as f:
                pass
                
        # Threading settings
        self.use_threading = use_threading
        self.max_workers = max_workers
        
        # Thread lock for file writing
        self.file_lock = threading.Lock()
    
    def get_archive_page(self):
        """Scrape the Pastebin archive page to get the latest paste IDs"""
        logger.info("Fetching Pastebin archive page")
        try:
            response = requests.get(ARCHIVE_URL, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Updated selector - first look for the main table
            main_table = soup.find('table', class_='maintable')
            if not main_table:
                logger.error("Could not find main table on archive page")
                return []
                
            # Find all links within the table rows
            paste_links = []
            for row in main_table.find_all('tr'):
                # Look for the first cell in each row
                if row.find('td'):
                    links = row.find('td').find_all('a')
                    paste_links.extend(links)
            
            # Extract paste IDs from the links
            paste_ids = []
            for link in paste_links:
                href = link.get('href')
                if href and href.startswith('/'):
                    paste_ids.append(href[1:])  # Remove the leading '/'
            
            logger.info(f"Found {len(paste_ids)} paste IDs in archive")
            return paste_ids
            
        except requests.RequestException as e:
            logger.error(f"Error fetching archive page: {e}")
            return []
    
    def get_paste_content(self, paste_id):
        """Fetch the raw content of a paste given its ID"""
        url = RAW_URL_TEMPLATE.format(paste_id)
        logger.info(f"Fetching paste content: {paste_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching paste {paste_id}: {e}")
            return None
    
    def check_keywords(self, content):
        """Check if the content contains any of the target keywords"""
        if not content:
            return []
        
        # Convert content to lowercase for case-insensitive matching
        content_lower = content.lower()
        
        # Check for crypto keywords
        crypto_matches = [keyword for keyword in CRYPTO_KEYWORDS 
                         if keyword.lower() in content_lower]
        
        # Check for telegram links
        telegram_matches = [keyword for keyword in TELEGRAM_KEYWORDS 
                           if keyword.lower() in content_lower]
        
        return list(set(crypto_matches + telegram_matches))
    
    def save_match(self, paste_id, keywords):
        """Save a matching paste to the output file"""
        now = datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        
        # Determine context based on found keywords
        if any(k in CRYPTO_KEYWORDS for k in keywords) and any(k in TELEGRAM_KEYWORDS for k in keywords):
            context = f"Found crypto and Telegram content in Pastebin paste ID {paste_id}"
        elif any(k in CRYPTO_KEYWORDS for k in keywords):
            context = f"Found crypto-related content in Pastebin paste ID {paste_id}"
        else:
            context = f"Found Telegram link in Pastebin paste ID {paste_id}"
        
        match_data = {
            "source": "pastebin",
            "context": context,
            "paste_id": paste_id,
            "url": RAW_URL_TEMPLATE.format(paste_id),
            "discovered_at": now,
            "keywords_found": keywords,
            "status": "pending"
        }
        
        # Use lock when writing to file in threaded mode
        with self.file_lock:
            with open(OUTPUT_FILE, 'a') as f:
                f.write(json.dumps(match_data) + '\n')
        
        logger.info(f"Saved match for paste {paste_id} with keywords: {', '.join(keywords)}")
    
    def process_paste(self, paste_id):
        """Process a single paste - used for both threaded and non-threaded modes"""
        # Add random delay between requests to avoid rate limiting
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)
        
        content = self.get_paste_content(paste_id)
        
        if content:
            keywords_found = self.check_keywords(content)
            
            if keywords_found:
                logger.info(f"Paste {paste_id} contains keywords: {', '.join(keywords_found)}")
                self.save_match(paste_id, keywords_found)
                return True
            else:
                logger.info(f"No keywords found in paste {paste_id}")
        
        return False
    
    def crawl(self):
        """Main crawling function to process Pastebin archive"""
        paste_ids = self.get_archive_page()
        
        if not paste_ids:
            logger.error("No paste IDs found. Exiting.")
            return
        
        matches_count = 0
        
        if self.use_threading:
            logger.info(f"Starting threaded crawl with {self.max_workers} workers")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all paste IDs for processing
                future_to_paste = {executor.submit(self.process_paste, paste_id): paste_id for paste_id in paste_ids}
                
                # Process results as they complete
                for future in future_to_paste:
                    if future.result():
                        matches_count += 1
        else:
            logger.info("Starting sequential crawl")
            for paste_id in paste_ids:
                if self.process_paste(paste_id):
                    matches_count += 1
            
        logger.info(f"Crawling complete. Processed {len(paste_ids)} pastes, found {matches_count} matches.")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Pastebin Keyword Crawler')
    parser.add_argument('--threading', action='store_true', help='Enable multi-threading')
    parser.add_argument('--workers', type=int, default=5, help='Number of worker threads (default: 5)')
    return parser.parse_args()

def main():
    """Main function to run the crawler"""
    args = parse_arguments()
    
    logger.info("Starting Pastebin keyword crawler")
    
    if args.threading:
        logger.info(f"Threading enabled with {args.workers} workers")
    else:
        logger.info("Threading disabled, using sequential processing")
    
    crawler = PastebinCrawler(use_threading=args.threading, max_workers=args.workers)
    crawler.crawl()
    logger.info("Crawler finished execution")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Crawler stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True) 