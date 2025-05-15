# Pastebin Keyword Crawler

A Python application that scrapes Pastebin's public archive for pastes containing keywords related to cryptocurrency or Telegram links.

## Features

- Scrapes the latest pastes from Pastebin's archive
- Detects crypto-related keywords and Telegram links
- Stores matching results in JSONL format
- Implements rate limiting to avoid being blocked
- Includes logging for tracking processed pastes
- Optional multithreading support for faster processing
- **NEW**: Web interface for easy configuration and result visualization

## Installation

1. Clone this repository
2. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

### Web Interface (Recommended)

Run the Flask web application:

```
python app.py
```

Then open your browser and navigate to:
- http://localhost:5000

The web interface allows you to:
- Configure crypto and Telegram keywords
- Set the number of pastes to process
- Enable/disable multithreading
- Monitor progress in real-time
- View and download results

### Command Line Usage

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

The application:
1. Scrapes Pastebin's archive page
2. Processes each paste to check for keywords
3. Saves matches to `keyword_matches.jsonl`
4. Logs all activity to `crawler.log`

## Web Application Features

The web interface offers several advantages:
1. **User-friendly Configuration**: Easily adjust search terms and crawler settings
2. **Real-time Progress Monitoring**: Watch the crawler's progress with a visual indicator
3. **Results Visualization**: View matching pastes in an organized, readable format
4. **Download Option**: Download results as a JSONL file with one click
5. **Responsive Design**: Works on desktop and mobile devices

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
4. **Validation Tool**: Script to analyze and validate the crawler results
5. **Web Interface**: Visual application for easy configuration and result viewing
