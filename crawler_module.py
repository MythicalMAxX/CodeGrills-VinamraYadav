#!/usr/bin/env python3
"""
Pastebin Keyword Crawler Module

This module scrapes Pastebin's public archive for pastes containing 
crypto-related keywords or Telegram links, and saves them to a JSONL file.
It's designed to be imported and used by other applications.
"""

import os
import re
import json
import time
import random
import logging
import datetime
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

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
DEFAULT_OUTPUT_FILE = "keyword_matches.jsonl"
MIN_DELAY = 1.5
MAX_DELAY = 3.5

# Default keywords to search for
DEFAULT_CRYPTO_KEYWORDS = [
    "crypto", "bitcoin", "btc", "ethereum", "eth", "blockchain", 
    "binance", "coinbase", "wallet", "nft", "token", "altcoin",
    "defi", "mining", "staking", "ledger", "metamask", "dogecoin",
    "ripple", "xrp", "solana", "cardano", "ada"
]
DEFAULT_TELEGRAM_KEYWORDS = ["t.me", "telegram.me", "telegram"]

class PastebinCrawler:
    """Crawler for extracting and analyzing Pastebin content based on keywords"""
    
    def __init__(self, use_threading=False, max_workers=5, 
                 output_file=DEFAULT_OUTPUT_FILE, 
                 crypto_keywords=None, telegram_keywords=None,
                 max_pastes=30, callback=None):
        """Initialize the crawler with settings
        
        Args:
            use_threading (bool): Whether to use threading for faster processing
            max_workers (int): Maximum number of worker threads if threading is enabled
            output_file (str): Path to save the matching results
            crypto_keywords (list): Custom list of crypto keywords to search for
            telegram_keywords (list): Custom list of Telegram keywords to search for
            max_pastes (int): Maximum number of pastes to process (0 for all available)
            callback (function): Callback function for progress updates
        """
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Threading settings
        self.use_threading = use_threading
        self.max_workers = max_workers
        
        # Output settings
        self.output_file = output_file
        
        # Create output file if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        if not os.path.exists(output_file):
            with open(output_file, 'w') as f:
                pass
        
        # Keywords to search for
        self.crypto_keywords = crypto_keywords or DEFAULT_CRYPTO_KEYWORDS
        self.telegram_keywords = telegram_keywords or DEFAULT_TELEGRAM_KEYWORDS
        
        # Maximum pastes to process
        self.max_pastes = max_pastes
        
        # Progress callback
        self.callback = callback
        
        # Results storage
        self.results = []
        
        # Thread lock for file writing and results access
        self.file_lock = threading.Lock()
        
        # Progress tracking
        self.processed_count = 0
        self.matches_count = 0
        self.total_pastes = 0
    
    def update_progress(self, status, progress=None, message=None):
        """Update progress via callback if provided"""
        if self.callback:
            self.callback(status=status, progress=progress, message=message)
    
    def get_archive_page(self):
        """Scrape the Pastebin archive page to get the latest paste IDs"""
        logger.info("Fetching Pastebin archive page")
        self.update_progress(status="fetching", message="Fetching Pastebin archive page...")
        
        try:
            response = requests.get(ARCHIVE_URL, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for the main table
            main_table = soup.find('table', class_='maintable')
            if not main_table:
                logger.error("Could not find main table on archive page")
                self.update_progress(status="error", message="Could not find paste archive table")
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
            
            # Limit the number of pastes if requested
            if self.max_pastes > 0 and len(paste_ids) > self.max_pastes:
                paste_ids = paste_ids[:self.max_pastes]
                
            self.total_pastes = len(paste_ids)
            logger.info(f"Found {len(paste_ids)} paste IDs in archive")
            self.update_progress(
                status="processing", 
                progress=0, 
                message=f"Found {len(paste_ids)} pastes. Starting processing..."
            )
            return paste_ids
            
        except requests.RequestException as e:
            error_msg = f"Error fetching archive page: {e}"
            logger.error(error_msg)
            self.update_progress(status="error", message=error_msg)
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
        crypto_matches = [keyword for keyword in self.crypto_keywords 
                         if keyword.lower() in content_lower]
        
        # Check for telegram links
        telegram_matches = [keyword for keyword in self.telegram_keywords 
                           if keyword.lower() in content_lower]
        
        return list(set(crypto_matches + telegram_matches))
    
    def save_match(self, paste_id, keywords):
        """Save a matching paste to the output file and results list"""
        now = datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds') + 'Z'
        
        # Determine context based on found keywords
        has_crypto = any(k in self.crypto_keywords for k in keywords)
        has_telegram = any(k in self.telegram_keywords for k in keywords)
        
        if has_crypto and has_telegram:
            context = f"Found crypto and Telegram content in Pastebin paste ID {paste_id}"
        elif has_crypto:
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
        
        # Use lock when writing to file and updating results
        with self.file_lock:
            with open(self.output_file, 'a') as f:
                f.write(json.dumps(match_data) + '\n')
            self.results.append(match_data)
            self.matches_count += 1
        
        logger.info(f"Saved match for paste {paste_id} with keywords: {', '.join(keywords)}")
    
    def process_paste(self, paste_id):
        """Process a single paste - used for both threaded and non-threaded modes"""
        # Add random delay between requests to avoid rate limiting
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)
        
        content = self.get_paste_content(paste_id)
        
        # Update progress
        with self.file_lock:
            self.processed_count += 1
            progress = int((self.processed_count / self.total_pastes) * 100) if self.total_pastes else 0
            
        self.update_progress(
            status="processing", 
            progress=progress, 
            message=f"Processing paste {self.processed_count} of {self.total_pastes}"
        )
        
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
        # Reset counters
        self.processed_count = 0
        self.matches_count = 0
        self.results = []
        
        paste_ids = self.get_archive_page()
        
        if not paste_ids:
            error_msg = "No paste IDs found. Exiting."
            logger.error(error_msg)
            self.update_progress(status="error", message=error_msg)
            return []
        
        if self.use_threading and len(paste_ids) > 1:
            logger.info(f"Starting threaded crawl with {self.max_workers} workers")
            self.update_progress(
                status="processing", 
                message=f"Starting threaded processing with {self.max_workers} workers"
            )
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all paste IDs for processing
                future_to_paste = {executor.submit(self.process_paste, paste_id): paste_id for paste_id in paste_ids}
                
                # Process results as they complete
                for future in future_to_paste:
                    future.result()  # Wait for completion but don't need the result directly
        else:
            logger.info("Starting sequential crawl")
            self.update_progress(status="processing", message="Starting sequential processing")
            
            for paste_id in paste_ids:
                self.process_paste(paste_id)
            
        logger.info(f"Crawling complete. Processed {self.processed_count} pastes, found {self.matches_count} matches.")
        self.update_progress(
            status="complete", 
            progress=100, 
            message=f"Completed! Processed {self.processed_count} pastes, found {self.matches_count} matches."
        )
        
        return self.results
        
def crawl_pastebin(crypto_keywords=None, telegram_keywords=None, 
                  use_threading=True, max_workers=5, 
                  output_file=DEFAULT_OUTPUT_FILE, max_pastes=30,
                  callback=None):
    """
    Simplified function to initiate a crawl with the given parameters
    
    Args:
        crypto_keywords (list): Custom list of crypto keywords to search for
        telegram_keywords (list): Custom list of Telegram keywords to search for
        use_threading (bool): Whether to use threading for faster processing
        max_workers (int): Maximum number of worker threads if threading is enabled
        output_file (str): Path to save the matching results
        max_pastes (int): Maximum number of pastes to process (0 for all available)
        callback (function): Callback function for progress updates
        
    Returns:
        list: List of matching paste data
    """
    crawler = PastebinCrawler(
        use_threading=use_threading,
        max_workers=max_workers,
        output_file=output_file,
        crypto_keywords=crypto_keywords,
        telegram_keywords=telegram_keywords,
        max_pastes=max_pastes,
        callback=callback
    )
    
    return crawler.crawl() 