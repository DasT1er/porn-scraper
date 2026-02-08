#!/usr/bin/env python3
"""
Modern Web UI for Gallery Scraper
Flask-based web interface with real-time progress tracking
"""

import asyncio
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from queue import Queue

import yaml
from flask import Flask, render_template, request, jsonify, Response, send_from_directory

from scraper_v2 import HybridScraper, GalleryDetector, ImageDownloader, MetadataExtractor

app = Flask(__name__)

# ── Job tracking ──────────────────────────────────────────────────────────────
jobs = {}  # job_id -> job_info
job_logs = {}  # job_id -> list of log messages


class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def load_config(config_path="config.yaml"):
    """Load config from YAML file"""
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def save_config(config, config_path="config.yaml"):
    """Save config to YAML file"""
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def add_log(job_id, message, level="info"):
    """Add a log message to a job"""
    if job_id not in job_logs:
        job_logs[job_id] = []
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "message": message,
        "level": level,
    }
    job_logs[job_id].append(entry)


def run_scrape_job(job_id, url, mode, output_dir=None):
    """Run a scrape job in a background thread"""
    jobs[job_id]["status"] = JobStatus.RUNNING
    jobs[job_id]["started_at"] = datetime.now().isoformat()
    add_log(job_id, f"Starting scrape: {url}", "info")
    add_log(job_id, f"Mode: {mode}", "info")

    try:
        scraper = HybridScraper()
        output_path = Path(output_dir) if output_dir else None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Redirect console output to job logs
        from io import StringIO
        from rich.console import Console

        buffer = StringIO()
        scraper_console = Console(file=buffer, force_terminal=False, no_color=True)

        # Monkey-patch the scraper's console temporarily
        import scraper_v2
        original_console = scraper_v2.console
        scraper_v2.console = scraper_console

        try:
            loop.run_until_complete(
                scraper.scrape_gallery(url, output_path, mode)
            )

            # Capture console output
            output = buffer.getvalue()
            for line in output.strip().split("\n"):
                line = line.strip()
                if line:
                    add_log(job_id, line, "info")

            jobs[job_id]["status"] = JobStatus.COMPLETED
            add_log(job_id, "Scraping completed successfully!", "success")
        finally:
            scraper_v2.console = original_console
            loop.close()

    except Exception as e:
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["error"] = str(e)
        add_log(job_id, f"Error: {e}", "error")

    jobs[job_id]["finished_at"] = datetime.now().isoformat()


def run_batch_job(job_id, urls, mode):
    """Run a batch scrape job in a background thread"""
    jobs[job_id]["status"] = JobStatus.RUNNING
    jobs[job_id]["started_at"] = datetime.now().isoformat()
    jobs[job_id]["total"] = len(urls)
    jobs[job_id]["current"] = 0
    add_log(job_id, f"Starting batch scrape: {len(urls)} URLs", "info")

    try:
        scraper = HybridScraper()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        import scraper_v2
        from io import StringIO
        from rich.console import Console

        buffer = StringIO()
        scraper_console = Console(file=buffer, force_terminal=False, no_color=True)
        original_console = scraper_v2.console
        scraper_v2.console = scraper_console

        try:
            for i, url in enumerate(urls, 1):
                jobs[job_id]["current"] = i
                add_log(job_id, f"Gallery {i}/{len(urls)}: {url}", "info")

                try:
                    loop.run_until_complete(
                        scraper.scrape_gallery(url, mode=mode)
                    )
                    add_log(job_id, f"Gallery {i} completed", "success")
                except Exception as e:
                    add_log(job_id, f"Gallery {i} failed: {e}", "error")

                # Capture output
                output = buffer.getvalue()
                buffer.truncate(0)
                buffer.seek(0)
                for line in output.strip().split("\n"):
                    line = line.strip()
                    if line:
                        add_log(job_id, line, "info")

            jobs[job_id]["status"] = JobStatus.COMPLETED
            add_log(job_id, "Batch scraping completed!", "success")
        finally:
            scraper_v2.console = original_console
            loop.close()

    except Exception as e:
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["error"] = str(e)
        add_log(job_id, f"Error: {e}", "error")

    jobs[job_id]["finished_at"] = datetime.now().isoformat()


def run_category_job(job_id, url, mode, max_pages):
    """Run a category scrape job in a background thread"""
    jobs[job_id]["status"] = JobStatus.RUNNING
    jobs[job_id]["started_at"] = datetime.now().isoformat()
    add_log(job_id, f"Scanning category: {url}", "info")
    add_log(job_id, f"Max pages: {max_pages}", "info")

    try:
        from scraper_ui import CategoryDetector

        detector = CategoryDetector()
        gallery_links = detector.detect_gallery_links(url, max_pages)

        if not gallery_links:
            jobs[job_id]["status"] = JobStatus.COMPLETED
            add_log(job_id, "No galleries found in category", "warning")
            jobs[job_id]["finished_at"] = datetime.now().isoformat()
            return

        jobs[job_id]["total"] = len(gallery_links)
        jobs[job_id]["current"] = 0
        jobs[job_id]["galleries_found"] = len(gallery_links)
        add_log(job_id, f"Found {len(gallery_links)} galleries", "success")

        scraper = HybridScraper()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        import scraper_v2
        from io import StringIO
        from rich.console import Console

        buffer = StringIO()
        scraper_console = Console(file=buffer, force_terminal=False, no_color=True)
        original_console = scraper_v2.console
        scraper_v2.console = scraper_console

        try:
            for i, gallery_url in enumerate(gallery_links, 1):
                jobs[job_id]["current"] = i
                add_log(job_id, f"Gallery {i}/{len(gallery_links)}: {gallery_url}", "info")

                try:
                    loop.run_until_complete(
                        scraper.scrape_gallery(gallery_url, mode=mode)
                    )
                    add_log(job_id, f"Gallery {i} completed", "success")
                except Exception as e:
                    add_log(job_id, f"Gallery {i} failed: {e}", "error")

                output = buffer.getvalue()
                buffer.truncate(0)
                buffer.seek(0)
                for line in output.strip().split("\n"):
                    line = line.strip()
                    if line:
                        add_log(job_id, line, "info")

            jobs[job_id]["status"] = JobStatus.COMPLETED
            add_log(job_id, "Category scraping completed!", "success")
        finally:
            scraper_v2.console = original_console
            loop.close()

    except Exception as e:
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["error"] = str(e)
        add_log(job_id, f"Error: {e}", "error")

    jobs[job_id]["finished_at"] = datetime.now().isoformat()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    """Start a single gallery scrape job"""
    data = request.json
    url = data.get("url", "").strip()
    mode = data.get("mode", "auto")
    output_dir = data.get("output_dir", "")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "type": "single",
        "url": url,
        "mode": mode,
        "status": JobStatus.QUEUED,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "finished_at": None,
    }

    thread = threading.Thread(
        target=run_scrape_job,
        args=(job_id, url, mode, output_dir or None),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"})


@app.route("/api/scrape/batch", methods=["POST"])
def start_batch_scrape():
    """Start a batch scrape job"""
    data = request.json
    urls_text = data.get("urls", "").strip()
    mode = data.get("mode", "auto")

    urls = [u.strip() for u in urls_text.split("\n") if u.strip() and not u.strip().startswith("#")]

    if not urls:
        return jsonify({"error": "No valid URLs provided"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "type": "batch",
        "url": f"{len(urls)} URLs",
        "mode": mode,
        "status": JobStatus.QUEUED,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "finished_at": None,
        "total": len(urls),
        "current": 0,
    }

    thread = threading.Thread(
        target=run_batch_job,
        args=(job_id, urls, mode),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued", "total": len(urls)})


@app.route("/api/scrape/category", methods=["POST"])
def start_category_scrape():
    """Start a category scrape job"""
    data = request.json
    url = data.get("url", "").strip()
    mode = data.get("mode", "auto")
    max_pages = data.get("max_pages", 10)

    if not url:
        return jsonify({"error": "URL is required"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "type": "category",
        "url": url,
        "mode": mode,
        "status": JobStatus.QUEUED,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "finished_at": None,
        "total": 0,
        "current": 0,
    }

    thread = threading.Thread(
        target=run_category_job,
        args=(job_id, url, mode, max_pages),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"})


@app.route("/api/jobs")
def list_jobs():
    """List all jobs"""
    job_list = sorted(
        jobs.values(),
        key=lambda j: j.get("created_at", ""),
        reverse=True,
    )
    return jsonify(job_list)


@app.route("/api/jobs/<job_id>")
def get_job(job_id):
    """Get job details"""
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(jobs[job_id])


@app.route("/api/jobs/<job_id>/logs")
def get_job_logs(job_id):
    """Get job logs"""
    logs = job_logs.get(job_id, [])
    after = request.args.get("after", 0, type=int)
    return jsonify(logs[after:])


@app.route("/api/stream/<job_id>")
def stream_job(job_id):
    """Server-Sent Events stream for job progress"""
    def generate():
        last_log_index = 0
        while True:
            job = jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            logs = job_logs.get(job_id, [])
            new_logs = logs[last_log_index:]
            last_log_index = len(logs)

            event_data = {
                "status": job["status"],
                "logs": new_logs,
                "current": job.get("current", 0),
                "total": job.get("total", 0),
            }

            yield f"data: {json.dumps(event_data)}\n\n"

            if job["status"] in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                yield f"data: {json.dumps({'done': True, 'status': job['status']})}\n\n"
                break

            time.sleep(1)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/downloads")
def list_downloads():
    """List downloaded galleries"""
    config = load_config()
    download_dir = Path(config.get("download", {}).get("output_dir", "./downloads"))

    if not download_dir.exists():
        return jsonify([])

    galleries = []
    for entry in sorted(download_dir.iterdir(), key=lambda e: e.stat().st_mtime, reverse=True):
        if not entry.is_dir():
            continue

        # Count images
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        images = [f for f in entry.iterdir() if f.suffix.lower() in image_extensions]

        # Load metadata if available
        metadata = {}
        metadata_file = entry / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception:
                pass

        # Find first image as thumbnail
        thumbnail = None
        if images:
            thumbnail = f"/downloads/{entry.name}/{images[0].name}"

        total_size = sum(f.stat().st_size for f in images)

        galleries.append({
            "name": entry.name,
            "title": metadata.get("title", entry.name),
            "image_count": len(images),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "thumbnail": thumbnail,
            "tags": metadata.get("tags", []),
            "artist": metadata.get("artist"),
            "url": metadata.get("url", ""),
            "scraped_at": metadata.get("scraped_at", ""),
            "path": str(entry),
        })

    return jsonify(galleries)


@app.route("/downloads/<path:filepath>")
def serve_download(filepath):
    """Serve downloaded files"""
    config = load_config()
    download_dir = Path(config.get("download", {}).get("output_dir", "./downloads"))
    return send_from_directory(str(download_dir.resolve()), filepath)


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current settings"""
    config = load_config()
    return jsonify(config)


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update settings"""
    new_config = request.json
    save_config(new_config)
    return jsonify({"status": "ok"})


@app.route("/api/stats")
def get_stats():
    """Get dashboard statistics"""
    config = load_config()
    download_dir = Path(config.get("download", {}).get("output_dir", "./downloads"))

    total_galleries = 0
    total_images = 0
    total_size = 0
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    if download_dir.exists():
        for entry in download_dir.iterdir():
            if entry.is_dir():
                total_galleries += 1
                for f in entry.iterdir():
                    if f.suffix.lower() in image_extensions:
                        total_images += 1
                        total_size += f.stat().st_size

    active_jobs = sum(1 for j in jobs.values() if j["status"] == JobStatus.RUNNING)
    completed_jobs = sum(1 for j in jobs.values() if j["status"] == JobStatus.COMPLETED)

    return jsonify({
        "total_galleries": total_galleries,
        "total_images": total_images,
        "total_size_mb": round(total_size / 1024 / 1024, 1),
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs,
    })


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    """Start the web UI"""
    import webbrowser

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")

    print(f"""
 ╔══════════════════════════════════════════════════════╗
 ║                                                      ║
 ║   Gallery Scraper - Modern Web UI                    ║
 ║                                                      ║
 ║   Open in browser: http://{host}:{port}            ║
 ║                                                      ║
 ║   Press Ctrl+C to stop the server                    ║
 ║                                                      ║
 ╚══════════════════════════════════════════════════════╝
""")

    # Open browser automatically
    webbrowser.open(f"http://{host}:{port}")

    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
