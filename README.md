# Pastebin Keyword Crawler

A Python script that scrapes Pastebin's public archive for pastes containing keywords related to cryptocurrency or Telegram links.

## Features

- Scrapes the latest 30 pastes from Pastebin's archive
- Detects crypto-related keywords and Telegram links
- Stores matching results in JSONL format
- Implements rate limiting to avoid being blocked
- Includes logging for tracking processed pastes
- Optional multithreading support for faster processing

## Installation

1. Clone this repository
2. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the script with:

```
python pastebin_crawler.py
```

### With Multithreading

To enable multithreading for faster processing:

```
python pastebin_crawler.py --threading --workers 10
```

Options:
- `--threading`: Enable multithreading
- `--workers N`: Set the number of worker threads (default: 5)

### Validating Results

After running the crawler, you can validate and analyze the results with:

```
python validate_results.py
```

This will provide:
- Total number of matches found
- Number of unique paste IDs
- Frequency of each keyword
- Number of pastes containing both Telegram links and crypto terms

## How It Works

The script will:
1. Scrape Pastebin's archive page
2. Process each paste to check for keywords
3. Save matches to `keyword_matches.jsonl`
4. Log all activity to `crawler.log`

## Output Format

Each matching paste is stored as a JSON object in the following format:

```json
{
  "source": "pastebin",
  "context": "Found crypto-related content in Pastebin paste ID abc123",
  "paste_id": "abc123",
  "url": "https://pastebin.com/raw/abc123",
  "discovered_at": "2023-05-12T10:00:00Z",
  "keywords_found": ["crypto", "bitcoin"],
  "status": "pending"
}
```

## Implemented Bonus Features

1. **Rate Limiting**: Random delays between requests to avoid being blocked
2. **Multithreading**: Optional threading for faster processing
3. **Comprehensive Logging**: Detailed logs for monitoring and debugging
4. **Validation Tool**: Script to analyze and validate the crawler results # CodeGrills-VinamraYadav
