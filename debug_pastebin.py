#!/usr/bin/env python3
"""
Debug script to examine Pastebin's HTML structure
"""
import requests
from bs4 import BeautifulSoup

# Constants
ARCHIVE_URL = "https://pastebin.com/archive"

# Set up headers to mimic a browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def main():
    """Fetch and analyze the Pastebin archive page"""
    print(f"Fetching URL: {ARCHIVE_URL}")
    
    try:
        response = requests.get(ARCHIVE_URL, headers=headers)
        response.raise_for_status()
        
        # Print response status and content type
        print(f"Response status: {response.status_code}")
        print(f"Content type: {response.headers.get('Content-Type')}")
        
        # Print the first 500 characters of the response to get a feel for it
        print("\nFirst 500 characters of response:")
        print(response.text[:500])
        
        # Try to parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if we can find the archive table
        archive_table = soup.select('table.archive-table')
        print(f"\nFound archive tables: {len(archive_table)}")
        
        # Check if our original selector works
        paste_links = soup.select('table.archive-table tbody tr td:nth-child(1) a')
        print(f"Found paste links with original selector: {len(paste_links)}")
        
        # Try some alternative selectors
        alt_links1 = soup.find_all('a', class_='archive_title')
        print(f"Found links with 'archive_title' class: {len(alt_links1)}")
        
        # Print all table classes found
        tables = soup.find_all('table')
        print(f"\nFound {len(tables)} tables with classes:")
        for table in tables:
            print(f"Table class: {table.get('class')}")
        
        # Print a few links if found
        if alt_links1:
            print("\nSample links found:")
            for link in alt_links1[:5]:
                print(f"Link href: {link.get('href')}, text: {link.text}")
        
    except requests.RequestException as e:
        print(f"Error fetching page: {e}")

if __name__ == "__main__":
    main() 