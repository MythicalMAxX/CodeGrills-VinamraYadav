#!/usr/bin/env python3
"""
Flask Web App for Pastebin Keyword Crawler

A web interface for the Pastebin crawler that allows users to
customize search parameters and download results.
"""

import os
import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, url_for, redirect, flash, session

from crawler_module import crawl_pastebin, DEFAULT_CRYPTO_KEYWORDS, DEFAULT_TELEGRAM_KEYWORDS

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or str(uuid.uuid4())
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Folder for storing results
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
if not os.path.exists(RESULTS_FOLDER):
    os.makedirs(RESULTS_FOLDER)

# Storage management settings
MAX_TASK_AGE_HOURS = 24  # Tasks older than this will be cleaned up
MAX_RESULTS_FILES = 50    # Maximum number of result files to keep

# Global tasks dictionary to track running tasks
# Key: task_id, Value: {"status": str, "progress": int, "message": str, "results_file": str}
tasks = {}

def get_task_info(task_id):
    """Get information about a task"""
    if task_id not in tasks:
        return None
    return tasks[task_id]

def update_task_progress(task_id, status, progress=None, message=None):
    """Update the progress of a task"""
    if task_id in tasks:
        if status:
            tasks[task_id]["status"] = status
        if progress is not None:
            tasks[task_id]["progress"] = progress
        if message:
            tasks[task_id]["message"] = message

def crawler_callback(task_id):
    """Returns a callback function that updates the task progress"""
    def callback_fn(status, progress=None, message=None):
        update_task_progress(task_id, status, progress, message)
    return callback_fn

def run_crawler(task_id, crypto_keywords, telegram_keywords, 
                use_threading, max_workers, max_pastes):
    """Run the crawler in a background thread"""
    output_file = os.path.join(RESULTS_FOLDER, f"results_{task_id}.jsonl")
    
    try:
        # Start the crawler
        crawl_pastebin(
            crypto_keywords=crypto_keywords,
            telegram_keywords=telegram_keywords,
            use_threading=use_threading,
            max_workers=max_workers,
            output_file=output_file,
            max_pastes=max_pastes,
            callback=crawler_callback(task_id)
        )
        
        # Update task info with the results file
        with threading.Lock():
            tasks[task_id]["results_file"] = output_file
            tasks[task_id]["status"] = "complete"
            
    except Exception as e:
        # Handle any exceptions
        error_message = f"Error: {str(e)}"
        with threading.Lock():
            tasks[task_id]["status"] = "error"
            tasks[task_id]["message"] = error_message

def cleanup_old_tasks():
    """Clean up old tasks and their result files"""
    current_time = datetime.now()
    to_remove = []
    
    # Identify old tasks
    with threading.Lock():
        for task_id, task_info in tasks.items():
            created_at = datetime.fromisoformat(task_info["created_at"].replace('Z', '+00:00'))
            age = current_time - created_at
            
            # If task is completed and older than the max age, mark for removal
            if (task_info["status"] in ["complete", "error"] and 
                age > timedelta(hours=MAX_TASK_AGE_HOURS)):
                to_remove.append(task_id)
    
    # Remove old tasks and their files
    removed_count = 0
    for task_id in to_remove:
        with threading.Lock():
            task_info = tasks.pop(task_id, None)
            if task_info and task_info.get("results_file") and os.path.exists(task_info["results_file"]):
                try:
                    os.remove(task_info["results_file"])
                    removed_count += 1
                except OSError:
                    pass  # If we can't remove it, just continue
    
    if removed_count > 0:
        print(f"AUTO-CLEANUP: Removed {removed_count} old task files")

def cleanup_results_folder():
    """Limit the number of files in the results folder"""
    if not os.path.exists(RESULTS_FOLDER):
        return
        
    # Get all result files sorted by modification time (oldest first)
    result_files = []
    for filename in os.listdir(RESULTS_FOLDER):
        if filename.endswith('.jsonl'):
            file_path = os.path.join(RESULTS_FOLDER, filename)
            result_files.append((file_path, os.path.getmtime(file_path)))
    
    # Sort by modification time (oldest first)
    result_files.sort(key=lambda x: x[1])
    
    # Remove oldest files if we have more than the max
    removed_count = 0
    if len(result_files) > MAX_RESULTS_FILES:
        for file_path, _ in result_files[:(len(result_files) - MAX_RESULTS_FILES)]:
            try:
                os.remove(file_path)
                removed_count += 1
            except OSError:
                pass  # If we can't remove it, just continue
    
    if removed_count > 0:
        print(f"AUTO-CLEANUP: Removed {removed_count} oldest result files. {len(result_files) - removed_count} files remain.")

# Start a background thread for periodic cleanup
def start_cleanup_thread():
    """Start a background thread that periodically cleans up old tasks and files"""
    def cleanup_worker():
        print("AUTO-CLEANUP: Starting scheduled cleanup thread")
        while True:
            print("\nAUTO-CLEANUP: Running scheduled cleanup task")
            cleanup_old_tasks()
            cleanup_results_folder()
            # Print status after cleanup
            print(f"AUTO-CLEANUP: Current task count: {len(tasks)}")
            print(f"AUTO-CLEANUP: Next cleanup in 5 minutes")
            time.sleep(300)  # Run cleanup every 5 minutes instead of hourly
    
    cleanup_thread = threading.Thread(target=cleanup_worker)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    print("AUTO-CLEANUP: Cleanup thread started")

# Start the cleanup thread when the app starts
start_cleanup_thread()

@app.route('/')
def index():
    """Render the main page"""
    crypto_keywords = DEFAULT_CRYPTO_KEYWORDS
    telegram_keywords = DEFAULT_TELEGRAM_KEYWORDS
    
    return render_template(
        'index.html',
        crypto_keywords=crypto_keywords,
        telegram_keywords=telegram_keywords
    )

@app.route('/start_crawler', methods=['POST'])
def start_crawler():
    """Start a new crawler task"""
    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # Get form data
    crypto_keywords = request.form.get('crypto_keywords', '').split(',')
    crypto_keywords = [k.strip() for k in crypto_keywords if k.strip()]
    
    telegram_keywords = request.form.get('telegram_keywords', '').split(',')
    telegram_keywords = [k.strip() for k in telegram_keywords if k.strip()]
    
    use_threading = request.form.get('use_threading') == 'on'
    max_workers = int(request.form.get('max_workers', 5))
    max_pastes = int(request.form.get('max_pastes', 30))
    
    # Initialize task
    tasks[task_id] = {
        "status": "initializing",
        "progress": 0,
        "message": "Initializing crawler...",
        "results_file": None,
        "created_at": datetime.now().isoformat()
    }
    
    # Start crawler in a background thread
    thread = threading.Thread(
        target=run_crawler,
        args=(task_id, crypto_keywords, telegram_keywords, use_threading, max_workers, max_pastes)
    )
    thread.daemon = True
    thread.start()
    
    # Run a quick cleanup of old tasks
    cleanup_old_tasks()
    
    # Return task ID
    return jsonify({"task_id": task_id})

@app.route('/task_status/<task_id>')
def task_status(task_id):
    """Get the status of a task"""
    task_info = get_task_info(task_id)
    if not task_info:
        return jsonify({"status": "not_found"}), 404
    
    return jsonify(task_info)

@app.route('/results/<task_id>')
def get_results(task_id):
    """Get the results of a completed task"""
    task_info = get_task_info(task_id)
    if not task_info:
        flash("Task not found", "error")
        return redirect(url_for('index'))
    
    if task_info["status"] != "complete":
        flash("Task is not complete yet", "warning")
        return redirect(url_for('index'))
    
    if not task_info["results_file"] or not os.path.exists(task_info["results_file"]):
        flash("Results file not found", "error")
        return redirect(url_for('index'))
    
    # Read the results file
    results = []
    with open(task_info["results_file"], 'r') as f:
        for line in f:
            if line.strip():
                try:
                    results.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass
    
    # Return the results as a simple summary
    return render_template(
        'results.html',
        task_id=task_id,
        results=results,
        count=len(results)
    )

@app.route('/download/<task_id>')
def download_results(task_id):
    """Download the results file"""
    task_info = get_task_info(task_id)
    if not task_info:
        flash("Task not found", "error")
        return redirect(url_for('index'))
    
    if not task_info["results_file"] or not os.path.exists(task_info["results_file"]):
        flash("Results file not found", "error")
        return redirect(url_for('index'))
    
    return send_file(
        task_info["results_file"],
        mimetype='application/json',
        as_attachment=True,
        download_name='keyword_matches.jsonl'
    )

@app.route('/cleanup/<task_id>', methods=['POST'])
def cleanup_task(task_id):
    """Clean up a task after user has downloaded the results"""
    task_info = get_task_info(task_id)
    if not task_info:
        return jsonify({"status": "not_found"}), 404
    
    # Remove the results file if it exists
    if task_info.get("results_file") and os.path.exists(task_info["results_file"]):
        try:
            os.remove(task_info["results_file"])
            print(f"MANUAL-CLEANUP: Removed file for task {task_id}")
        except OSError as e:
            print(f"MANUAL-CLEANUP: Failed to remove file for task {task_id}: {e}")
    
    # Remove the task from the tasks dictionary
    with threading.Lock():
        tasks.pop(task_id, None)
        print(f"MANUAL-CLEANUP: Removed task {task_id} from memory")
    
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 