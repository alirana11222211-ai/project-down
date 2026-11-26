import os
import uuid
import threading
import subprocess
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# job_id -> {"status": "processing|done|error", "file": filename or None, "error": msg}
jobs = {}

def download_task(video_url, job_id):
    """Runs yt-dlp in a background thread and saves an mp4 into DOWNLOAD_DIR."""
    try:
        output_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
        
        cmd = [
            "python", "-m", "yt_dlp",
            "--extractor-args", "youtube:player_client=tv,mweb",
            "--extractor-args", "youtubepot-bgutilhttp:base_url=https://bgutil-pot-latest-1crq.onrender.com",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--no-playlist",
            video_url,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            jobs[job_id] = {"status": "error", "error": result.stderr[-500:] or "yt-dlp failed"}
            return

        # Find the produced file (yt-dlp may produce .mp4 or .mkv etc.)
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(job_id + "."):
                jobs[job_id] = {"status": "done", "file": f}
                return

        jobs[job_id] = {"status": "error", "error": "Output file not found"}
    except Exception as e:
        jobs[job_id] = {"status": "error", "error": str(e)}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify({"error": "Only YouTube links are supported"}), 400

    job_id = uuid.uuid4().hex
    jobs[job_id] = {"status": "processing"}
    threading.Thread(target=download_task, args=(url, job_id), daemon=True).start()
    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "unknown"}), 404
    return jsonify(job)

@app.route("/api/file/<job_id>")
def get_file(job_id):
    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        return jsonify({"error": "Not ready"}), 404
    return send_from_directory(DOWNLOAD_DIR, job["file"], as_attachment=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
